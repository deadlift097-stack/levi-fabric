"""Bytecode -> C++ for the supported subset (straight-line code).

Anything outside the subset is NEVER silently dropped: it becomes a
`// TODO(levipack-forge)` comment in the C++ and an entry in the report.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from . import classfile as C

LOG_LEVELS = {"trace": "debug", "debug": "debug", "info": "info", "warn": "warn", "error": "error"}
LOGGER_OWNERS = {"org/slf4j/Logger", "org/apache/logging/log4j/Logger"}
# Fabric lifecycle events that map onto the Levi mod lifecycle.
ENABLE_EVENTS = {"SERVER_STARTING", "SERVER_STARTED", "CLIENT_STARTED"}
DISABLE_EVENTS = {"SERVER_STOPPING", "SERVER_STOPPED", "CLIENT_STOPPING"}
LIFECYCLE_OWNER_HINTS = ("ServerLifecycleEvents", "ClientLifecycleEvents")


@dataclass
class Result:
    enable: list = field(default_factory=list)
    disable: list = field(default_factory=list)
    issues: list = field(default_factory=list)      # dicts: {where, what}
    converted: int = 0
    stubbed: int = 0


def cstr(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if ch == "\\": out.append("\\\\")
        elif ch == '"': out.append('\\"')
        elif ch == "\n": out.append("\\n")
        elif ch == "\r": out.append("\\r")
        elif ch == "\t": out.append("\\t")
        elif o < 32 or o == 127: out.append(f"\\x{o:02x}\"\"")
        else: out.append(ch)
    return '"' + "".join(out) + '"'


def fmt_value(v):
    k = v[0]
    if k == "str": return cstr(v[1])
    if k == "int": return str(v[1])
    if k == "long": return f"{v[1]}LL"
    if k == "float": return f"{v[1]!r}f"
    if k == "double": return repr(v[1])
    if k == "null": return "nullptr"
    return None


class Transpiler:
    def __init__(self, classes: dict[str, C.ClassFile], symbols=None, cfg_fields=None):
        self.classes = classes
        self.symbols = symbols      # SymbolIndex or None
        self.cfg_fields = cfg_fields or {}   # (owner, name) -> cpp config member
        self.res = Result()

    # ------------------------------------------------------------------ API
    def entry(self, cls_name: str, method_name: str, section: str):
        cf = self.classes.get(cls_name)
        if not cf:
            self.res.issues.append({"where": cls_name, "what": "entrypoint class not found in jar"})
            return
        m = cf.find_method(method_name)
        if not m or m.code is None:
            self.res.issues.append({"where": f"{cls_name}.{method_name}", "what": "entrypoint method not found"})
            return
        lines = self._method(cf, m, depth=0)
        getattr(self.res, section).extend(lines)

    # ------------------------------------------------------------- internals
    def _todo(self, where, what, lines):
        self.res.issues.append({"where": where, "what": what})
        self.res.stubbed += 1
        lines.append(f"// TODO(levipack-forge): {what}")
        if self.symbols is not None:
            for h in self.symbols.hints_for(what):
                lines.append(f"//   bedrock symbol candidate: {h}")

    def _method(self, cf, m, depth, args=None):
        where = f"{cf.name}.{m.name}{m.desc}"
        lines: list[str] = []
        if depth > 6:
            self._todo(where, "recursion limit while inlining lambdas", lines)
            return lines
        insns = C.decode(m.code)
        BRANCH = {153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
                  166, 167, 168, 170, 171, 198, 199, 200, 201, 191, 169}
        cut = next((k for k, i in enumerate(insns) if i.op in BRANCH), None)
        tail_todo = cut is not None
        if tail_todo:
            insns = insns[:cut]
        stack: list = []
        locals_: dict = {}
        if args:
            locals_.update(args)
        for ins in insns:
            op, a = ins.op, ins.arg
            if op == 0: continue
            elif op == 1: stack.append(("null",))
            elif 2 <= op <= 8: stack.append(("int", op - 3))
            elif op in (9, 10): stack.append(("long", op - 9))
            elif 11 <= op <= 13: stack.append(("float", float(op - 11)))
            elif op in (14, 15): stack.append(("double", float(op - 14)))
            elif op in (16, 17): stack.append(("int", a))
            elif op in (18, 19, 20):
                v = cf.const(a); stack.append(v if isinstance(v, tuple) else ("str", v))
            elif 26 <= op <= 45 or 21 <= op <= 25:
                if 21 <= op <= 25: idx = a
                else: idx = (op - 26) % 4
                stack.append(locals_.get(idx, ("this",) if idx == 0 else ("unknown",)))
            elif 54 <= op <= 58:
                locals_[a] = stack.pop()
            elif 59 <= op <= 78:
                locals_[(op - 59) % 4] = stack.pop()
            elif op == 87: stack.pop()
            elif op == 89: stack.append(stack[-1])
            elif op in (172, 173, 174, 175, 176, 177): break
            elif op == 178:
                o, n, d = cf.ref(a)
                stack.append(("static", o, n, d))
            elif op == 179:
                o, n, d = cf.ref(a); v = stack.pop()
                if (o, n) in self.cfg_fields: continue   # handled as typed config default
                if v[0] == "logger" or (o in self.classes and fmt_value(v) is not None):
                    continue
                self._todo(where, f"putstatic {o}.{n} with non-constant value", lines)
            elif op == 180:
                stack.pop(); stack.append(("unknown",))
            elif op == 181:
                stack.pop(); stack.pop()
                self._todo(where, "putfield (instance state) not supported", lines)
            elif op == 187: stack.append(("new", cf.cls(a)))
            elif op == 192: pass
            elif op in (182, 183, 184, 185):
                o, n, d = cf.ref(a)
                params, ret = C.arg_slots(d)
                call_args = [stack.pop() for _ in params][::-1]
                recv = None if op == 184 else stack.pop()
                out = self._call(cf, where, op, o, n, d, recv, call_args, depth, lines)
                if ret != "V":
                    stack.append(out if out else ("unknown",))
            elif op == 186:
                bsm, n, d = cf.invokedynamic(a)
                params, ret = C.arg_slots(d)
                cap = [stack.pop() for _ in params][::-1]
                target = self._lambda_target(cf, bsm)
                stack.append(("lambda", target, cap))
            else:
                self._todo(where, f"opcode 0x{op:02x} (arithmetic/array/etc.) outside supported subset", lines)
                return lines
        if tail_todo:
            self._todo(where, "code after the first branch/loop/try is outside the supported subset; "
                              "port the rest of this method by hand (the part above was converted)", lines)
        else:
            self.res.converted += 1
        return lines

    def _lambda_target(self, cf, bsm_index):
        mh, bargs = cf.bootstraps[bsm_index]
        for b in bargs:
            if cf.cp[b][0] == "mh":
                kind, (o, n, d) = cf.method_handle(b)
                return (o, n, d)
        return None

    def _call(self, cf, where, op, o, n, d, recv, args, depth, lines):
        # constructors / trivial plumbing
        if n == "<init>" and o in ("java/lang/Object",):
            return None
        if n == "getLogger" and ("LoggerFactory" in o or "LogManager" in o):
            return ("logger",)
        # autoboxing / unboxing is a no-op in C++
        if op == 184 and n == "valueOf" and o in ("java/lang/Integer", "java/lang/Boolean", "java/lang/Long",
                                                  "java/lang/Double", "java/lang/Float", "java/lang/Short", "java/lang/Byte") and args:
            return args[0]
        # logging
        if (o in LOGGER_OWNERS or (recv and recv[0] == "logger")) and n in LOG_LEVELS:
            return self._log(where, n, args, lines)
        if o == "java/io/PrintStream" and n in ("println", "print") and recv and recv[:3] == ("static", "java/lang/System", "out"):
            return self._log(where, "info", args[:1], lines)
        # Fabric lifecycle events
        if n == "register" and recv and recv[0] == "static" and any(h in recv[1] for h in LIFECYCLE_OWNER_HINTS):
            ev = recv[2]
            sect = "enable" if ev in ENABLE_EVENTS else "disable" if ev in DISABLE_EVENTS else None
            lam = args[0] if args else None
            if sect and lam and lam[0] == "lambda" and lam[1]:
                lo, ln_, ld = lam[1]
                tcf = self.classes.get(lo)
                tm = tcf.find_method(ln_, ld) if tcf else None
                if tm and tm.code is not None:
                    body = self._method(tcf, tm, depth + 1)
                    lines.append(f"// Fabric {recv[1].rsplit('/',1)[-1]}.{ev} -> LeviLauncher {sect}()")
                    if sect == "enable":
                        lines.extend(body)
                    else:
                        self.res.disable.extend(body)
                    return None
            self._todo(where, f"{recv[1]}.{ev}.register(...) callback could not be resolved", lines)
            return None
        # everything else: stub + symbol hints
        self._todo(where, f"unsupported call {o.replace('/', '.')}.{n}{d}", lines)
        return None

    def _log(self, where, level, args, lines):
        if not args:
            return None
        fmtv = args[0]
        if fmtv[0] != "str":
            self._todo(where, "logger call with non-constant message", lines)
            return None
        parts = [cstr(fmtv[1])]
        for v in args[1:]:
            f = fmt_value(v)
            if f is None and v[0] == "static" and (v[1], v[2]) in self.cfg_fields:
                f = f"mConfig.{self.cfg_fields[(v[1], v[2])]}"
            parts.append(f if f is not None else '"<runtime value>"')
        lines.append(f"self.getLogger().{LOG_LEVELS[level]}({', '.join(parts)});")
        return None

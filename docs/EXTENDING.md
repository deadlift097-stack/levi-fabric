# Extending the transpiler

* Call mapping lives in `Transpiler._call` (`levipack_forge/transpile.py`). Add a rule that returns C++ lines
  appended to `lines`; return a stack value if the Java method returns something.
* Unsupported bytecode must call `self._todo(...)` so it shows up in the report. Never drop code silently.
* Typical next steps: string concatenation (`StringConcatFactory`), `if (config.flag)` guards mapped to
  `mConfig` checks, command registration, item-use / tick events via `pl::memory::Hook`.

import json, os, pathlib, subprocess, shutil, sys, zipfile, tempfile
import pytest
from levipack_forge import classfile, fabricmeta, generator, symbols
from levipack_forge.transpile import cstr

FIX = pathlib.Path(__file__).parent / "fixtures" / "hello.jar"


def test_cstr_escapes():
    assert cstr('a"b\\n') == '"a\\"b\\\\n"'


def test_fabric_meta():
    m = fabricmeta.parse(json.dumps({"id": "x", "entrypoints": {"main": ["a.B", "a.C::go"]},
                                     "authors": [{"name": "N"}, "M"]}))
    assert m["entrypoints"]["main"] == [("a/B", None), ("a/C", "go")]
    assert m["authors"] == ["N", "M"]


@pytest.mark.skipif(not FIX.exists(), reason="fixture jar missing")
def test_parse_and_convert(tmp_path):
    with zipfile.ZipFile(FIX) as z:
        cf = classfile.parse(z.read("com/example/hello/HelloMod.class"))
    assert cf.name == "com/example/hello/HelloMod"
    r = generator.convert(FIX, tmp_path / "out")
    cpp = (tmp_path / "out/src/mod/MyMod.cpp").read_text()
    assert 'self.getLogger().info("Hello Fabric world!");' in cpp
    assert "mConfig.greeting" in cpp
    assert 'self.getLogger().warn("Bye");' in cpp        # lifecycle STOPPING -> disable()
    assert "TODO(levipack-forge)" in cpp                # loop was not silently dropped
    assert r["config_fields"] == 8   # 3 in HelloMod + 5 finite statics in Nasty
    cm = (tmp_path / "out/CMakeLists.txt").read_text()
    assert 'set(MOD_ID "hello_mod" CACHE' in cm


def test_symbol_search():
    idx = symbols.SymbolIndex(["_ZN6Player4jumpEv", "_ZN5Actor4hurtEv"])
    assert idx.search("Player", "jump") == ["_ZN6Player4jumpEv"]
    assert idx.hints_for("unsupported call net.minecraft.Player.jump()V") == ["_ZN6Player4jumpEv"]


def test_rescue_truncated_zip(tmp_path):
    big = os.urandom(1000) + b"_ZN6Player4jumpEv\x00" + b"A" * 200000
    full = tmp_path / "f.zip"
    with zipfile.ZipFile(full, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("libminecraftpe.so", big)
    cut = tmp_path / "cut.zip"
    cut.write_bytes(full.read_bytes()[:-200])           # chop central directory
    assert "_ZN6Player4jumpEv" in symbols.build_index(cut)


@pytest.mark.skipif(not FIX.exists(), reason="fixture jar missing")
def test_config_defaults_are_valid_cpp(tmp_path):
    generator.convert(FIX, tmp_path / "out")
    h = (tmp_path / "out/src/mod/Config.h").read_text()
    assert "= nan" not in h and "= inf" not in h          # NaN/Infinity statics are skipped
    assert "delete_ = 1" in h and "register_ = true" in h  # C++ keywords are renamed
    assert "(-9223372036854775807LL - 1)" in h

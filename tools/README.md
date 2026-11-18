# tools
`so_probe.py` inspects `libminecraftpe.so` (needs `pip install pyelftools`) and writes `symbols.json`
(vtable RVAs). `levipack-forge vtable --db symbols.json` prints it. Keep one file per game build, keyed by sha256.

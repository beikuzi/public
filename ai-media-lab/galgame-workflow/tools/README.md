# Safe Ren'Py archive and legacy script inspection

This page documents `safe_renpy.py`, an original Python 3 standard-library-only parser. The companion `render_clip.py` uses Pillow and FFmpeg; `prepare_demo.py` downloads the official demo only. No game assets, original dialogue, Ren'Py source, or bundled third-party libraries are included in this directory. See the top-level README_ZH.md for the full clip workflow.

## Commands

```sh
python safe_renpy.py list /path/to/game/data.rpa --output archive-index.json
python safe_renpy.py extract /path/to/game/data.rpa ./selected-assets bgs/school_roof_ni.jpg bgm/Aria.ogg
python safe_renpy.py rpyc /path/to/game/ZHS/script-a1-sunday-ZHS.rpyc --output private-script.json
python safe_renpy.py strings /path/to/game/ui_settings.rpyc --output private-strings.json
python -m unittest -v
```

Every output is newly created; existing files are never overwritten. Archive
extraction accepts exact member names, with no wildcard or extract-all action.
Code-related suffixes require an additional `--allow-code` flag. Extracted files
are created with mode 0600 and are never executed. Extraction uses POSIX directory
file descriptors and O_NOFOLLOW; on systems without those protections, listing
and RPYC inspection remain available but extraction explicitly refuses to run.

## Safety model and bounds

- RPA-3.0 only. Header and index offsets, member segments and prefix lengths are
  validated against the data region, excluding the compressed archive index.
- The index uses a custom primitive pickle interpreter. Global/class lookup,
  constructor, reduction, extension, persistent-ID and unknown opcodes are
  rejected. `pickle.loads`, `Unpickler`, dynamic imports, `eval`, `exec` and game
  execution are never used.
- Legacy zlib RPYC is parsed with `pickletools.genops`. Its inert-AST mode records
  whitelisted `renpy.ast` type names as inert data only. NEWOBJ requires empty
  arguments; BUILD copies dictionaries into those data records. PyCode's custom
  state stays opaque. No original class is imported or instantiated; REDUCE and
  all executable facilities remain forbidden.
- At most 32 MiB compressed / 64 MiB decompressed input; 2,000,000 opcodes;
  500,000 stack, memo, list or dictionary entries; 8 MiB per string; 128 MiB per
  extracted member and 512 MiB per extraction call. Metadata rendering is also
  depth/item bounded. These are defensive caps, not a formal OS-level sandbox.
- Absolute paths, traversal, backslashes, drive/ADS paths, control characters,
  Windows device names, case collisions, and file/directory collisions are
  rejected. Symlink traversal and overwrites are refused.
- The script command is a structural inventory, not a control-flow execution
  trace or general decompiler. Speaker is the source identifier. Scene/Show
  image identifiers still need matching to image definitions; this tool does
  not evaluate Python image-composition code. Only legacy zlib RPYC is supported,
  including an optional 16-byte source digest trailer; modern RPC2 is rejected.
- `strings` only scans textual opcode arguments; it does not claim executable
  opcodes are absent. Use this inspection fallback when inert-AST support is
  deliberately too narrow for a script. It never executes opcodes.

The supported RPA prefix accounting and legacy zlib RPYC format were checked
against the official demo's bundled loader/script implementation as a reference.
Tests are synthetic and asset-free. They cover primitive round-trips, forbidden
pickle operations, decompression bounds, malformed data, path traversal,
symlinks, offset/prefix bounds, collisions, overwrite refusal, and code opt-in.

Use only archives you are entitled to inspect. Extraction does not grant rights
to redistribute game assets, scripts, music, or footage; keep original and
intermediate game material outside any distributable tool bundle.

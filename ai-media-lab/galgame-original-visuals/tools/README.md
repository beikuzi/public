# Route A original-asset reconstruction

Prerequisites: Python 3, Pillow, NumPy, FFmpeg. Run from the folder that contains `tools`. Get the official free demo with the checksum-verifying helper, or provide the exact official archive via its `--archive` option:

    python tools/prepare_demo.py --destination local-game
    python tools/prepare_route_a.py
    python -m unittest discover -s tools -p 'test_safe_renpy.py' -v
    python tools/render_original.py --stills
    python tools/render_original.py

Outputs go to `deliverables`. Local assets and full local inspection data are NOT bundled in this source package and should not be republished as an asset or full-script archive.

The renderer is source-parameter reconstruction, not Ren'Py engine capture. Read `README_ZH.md` and `SCENE_ASSET_MAPPING.json` for exact scope/deviations. The strict parser never executes pickle globals, restored bytecode, Python, or Ren'Py scripts; its small AST whitelist intentionally refuses unsupported classes. The four unneeded AST files it refuses are not required for this scene. Derived code remains a local tool; third-party artwork, text, music and fonts retain their original rights.


## Public closeout snapshot · 2026-10-06

This is an archive of already-completed experimental source. Only source, licences and limited technical coverage/QA records are published. Videos, screenshots, game assets, full scripts and scene-text mappings are excluded. Historical verification claims retain their original scope; closeout checked source syntax, JSON validity and publication boundaries only, without rerunning games or adding features. Paths referring to private inputs must be prepared separately from legally obtained matching editions.

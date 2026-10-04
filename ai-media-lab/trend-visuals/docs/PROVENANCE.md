# Versioned evidence and compilation

`inputs/v5-compiled-snapshot.json` contains the initial90records,88coverage records and5qualitative synthesis groups. Those records remain unchanged; two excluded records are not included in coverage. The three initial official ranking sources and later three repeat observations are separate concepts, not additional independent sample votes.

`inputs/temporal/` contains typed public ranking observations and matched comparisons. No complete browser response archive is included. Missing ranks mean absent from the saved current sample, not necessarily absent from the whole platform. Rounded displayed metric differences are not exact underlying changes. Weibo's selected initial rows cannot establish an exhaustive new-entry list. Dates of source content, capture and the overall update are distinct.

`python build_data.py --check` verifies hashes and semantic consistency. `python build_data.py` compiles only local versioned inputs atomically. Missing or mismatched inputs fail before output writes; there is no network collection or synthetic fallback. Run `python qa/build-test.py` to exercise failures and determinism. Changes to inputs require explicit provenance and updated manifest hashes.

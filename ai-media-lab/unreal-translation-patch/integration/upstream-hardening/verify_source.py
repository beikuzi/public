"""Read-only verification of the exact reviewed patched source. No build/run."""
from pathlib import Path
import hashlib
import json
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python verify_source.py PATH_TO_PATCHED_UPSTREAM_SOURCE")
    root = Path(sys.argv[1]).resolve()
    manifest = json.loads(Path(__file__).with_name("static-checks.json").read_text())
    for relative, expected in manifest["files"].items():
        data = (root / relative).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected["patched_sha256"]:
            raise SystemExit(f"FAIL: source differs from reviewed patch: {relative}")
    network = (root / "src/NetworkClient.cpp").read_text()
    cache = (root / "src/VocabularyCache.cpp").read_text()
    logger = (root / "include/DebugLogger.hpp").read_text()
    if "SECURITY_FLAG_IGNORE_" in network:
        raise SystemExit("FAIL: TLS bypass remains")
    if "std::wofstream" in cache:
        raise SystemExit("FAIL: vocabulary output file sink remains")
    if "std::wofstream" in logger or "OutputDebugStringW(" in logger:
        raise SystemExit("FAIL: debug output sink remains")
    print(f"PASS: {len(manifest['files'])} exact patched files and static sink checks")
    print("Not compiled; not game-tested; not a whole-program safety proof.")


if __name__ == "__main__":
    main()

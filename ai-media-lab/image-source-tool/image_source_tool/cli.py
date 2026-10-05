import argparse
import sys
from pathlib import Path
from .imaging import InputError, prepare_image
from .manual import load_manual_records
from .providers import PROVIDERS, run_provider
from .report import build_report, write_reports


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local image provenance evidence. No network unless providers are explicitly selected and uploads permitted.")
    parser.add_argument("image", type=Path, help="Local still JPEG, PNG or WebP; URLs are not accepted")
    parser.add_argument("--providers", nargs="+", choices=PROVIDERS, default=[], help="Providers to request (default: offline only)")
    parser.add_argument("--allow-upload", nargs="+", choices=PROVIDERS, default=[], help="Explicit permission to share sanitized image pixels with each named provider")
    parser.add_argument("--output", type=Path, default=Path("private-output/latest"), help="Local private report directory")
    parser.add_argument("--manual-results", type=Path, help="Import local Ascii2D/SauceNAO browser records matched to this image hash; no network")
    parser.add_argument("--max-side", type=int, default=1600, help="Normalized maximum dimension, 128–1600 (default: 1600)")
    args = parser.parse_args(argv)
    try:
        prepared = prepare_image(args.image, args.max_side)
        # Validate manual records before any explicitly requested provider upload.
        manual = load_manual_records(args.manual_results, prepared.info["sha256"]) if args.manual_results else []
        results = [run_provider(provider, prepared, args.providers, args.allow_upload) for provider in PROVIDERS]
        results.extend(manual)
        report = build_report(prepared, results)
        write_reports(report, args.output)
    except InputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("Local file could not be read or report written. Check path and permissions.", file=sys.stderr)
        return 2
    print("Reports saved: " + str(args.output / "report.html") + " and report.json")
    for provider in results:
        mode = f' / manual {provider["method"]}' if provider.get("execution_mode") == "manual_record" else ""
        print(f'{provider["provider"]}{mode}: {provider["status"]} ({len(provider["candidates"])} candidates)')
    print("Identity and original authorship remain unverified. Review evidence and original posts.")
    return 0 if all(row["status"] in {"not_requested", "matches", "no_match"} for row in results) else 1

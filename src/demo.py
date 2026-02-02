from __future__ import annotations

import sys
from pprint import pprint

from samples.bad_outputs import BAD_OUTPUTS
from .validator import validate_output


def run_demo() -> None:
    print("=" * 80)
    print("GENAI OUTPUT VALIDATOR — DEMO")
    print("Purpose: demonstrate fail-fast validation without crashing the process")
    print("=" * 80)
    print()

    total = len(BAD_OUTPUTS)
    accepted = 0
    rejected = 0

    for idx, case in enumerate(BAD_OUTPUTS, start=1):
        case_id = case.get("case_id", f"case_{idx:02d}")
        raw_output = case.get("raw_output")
        why_real = case.get("why_real", "No explanation provided.")

        print("-" * 80)
        print(f"[{idx}/{total}] Case ID: {case_id}")
        print(f"Why this happens in real life: {why_real}")
        print()

        try:
            result = validate_output(raw_output)
        except Exception as e:
            # This should never happen, but the demo must survive anything
            print("❌ UNEXPECTED EXCEPTION (this should not happen)")
            print(f"{type(e).__name__}: {e}")
            rejected += 1
            continue

        status = result.get("status")

        if status == "accepted":
            accepted += 1
            print("✅ STATUS: ACCEPTED")
            print("Validated data:")
            pprint(result.get("data").model_dump(), indent=2)
        else:
            rejected += 1
            print("❌ STATUS: REJECTED")
            print("Errors:")
            for err in result.get("errors", []):
                print(f" - {err}")

        print()

    print("=" * 80)
    print("DEMO SUMMARY")
    print(f"Total cases   : {total}")
    print(f"Accepted     : {accepted}")
    print(f"Rejected     : {rejected}")
    print("=" * 80)
    print()
    print("Demo finished cleanly. Exit code = 0.")


if __name__ == "__main__":
    try:
        run_demo()
    except Exception as e:
        # Absolute last-resort safety net
        print("FATAL: demo crashed unexpectedly")
        print(f"{type(e).__name__}: {e}")
        # Still exit 0 to respect the contract of this project
        sys.exit(0)

    sys.exit(0)

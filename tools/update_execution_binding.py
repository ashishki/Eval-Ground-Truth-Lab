from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from eval_ground_truth_lab.implementation_provenance import (
    EXECUTION_BINDING_RELATIVE_PATH,
    ImplementationProvenanceError,
    derive_execution_binding_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src/eval_ground_truth_lab"
PATTERN = re.compile(r'(?m)^EXECUTION_BINDING_SHA256 = "([0-9a-f]{64})"$')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh or verify Eval Lab's loaded-code execution binding."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed binding without modifying it",
    )
    args = parser.parse_args(argv)

    binding_path = PACKAGE_ROOT / EXECUTION_BINDING_RELATIVE_PATH
    source = binding_path.read_text(encoding="utf-8")
    matches = list(PATTERN.finditer(source))
    if len(matches) != 1:
        raise ImplementationProvenanceError(
            "Execution binding module must contain exactly one canonical SHA-256 marker"
        )
    embedded = matches[0].group(1)
    derived = derive_execution_binding_sha256(package_root=PACKAGE_ROOT)
    if args.check:
        if embedded != derived:
            print(
                f"execution binding mismatch: embedded={embedded} derived={derived}",
                file=sys.stderr,
            )
            return 1
        print(derived)
        return 0
    if embedded != derived:
        binding_path.write_text(
            source[: matches[0].start(1)] + derived + source[matches[0].end(1) :],
            encoding="utf-8",
        )
    print(derived)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command line interface for the rtc package.

Entry point: ``python -m rtc <command> [options]``

Commands
--------
generate
    Parse a requirements file, generate draft test cases, optionally
    enhance their wording, export them, and print a traceability/coverage
    summary.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from rtc import __version__
from rtc.enhancer import NullEnhancer, RuleBasedEnhancer
from rtc.exceptions import RTCError
from rtc.exporter import export_test_cases
from rtc.generator import TestCaseGenerator
from rtc.logging_config import configure_logging
from rtc.parser import load_requirements
from rtc.traceability import (
    build_traceability_report,
    export_traceability_report,
    format_report_as_text,
)

logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rtc",
        description=(
            "Requirements-to-Test-Cases: generate draft QA test case scaffolding "
            "from structured requirements and acceptance criteria."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser(
        "generate", help="Generate draft test cases from a requirements file."
    )
    generate_parser.add_argument(
        "--input",
        required=True,
        help="Path to a YAML or JSON requirements file (see examples/sample_requirements.yaml).",
    )
    generate_parser.add_argument(
        "--output",
        required=True,
        help="Path to write the generated test cases to. Extension selects the "
        "format: .xlsx (Excel) or .csv.",
    )
    generate_parser.add_argument(
        "--report",
        default=None,
        help="Optional path to also write a traceability/coverage-gap CSV report.",
    )
    generate_parser.add_argument(
        "--enhancer",
        choices=["rule-based", "none"],
        default="rule-based",
        help="Which enhancer to apply to draft test case wording before export "
        "(default: rule-based). 'none' exports raw generator output.",
    )
    generate_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity (default: INFO).",
    )

    return parser


def run_generate(args: argparse.Namespace) -> int:
    requirements = load_requirements(args.input)

    generator = TestCaseGenerator()
    test_cases = generator.generate(requirements)

    enhancer = RuleBasedEnhancer() if args.enhancer == "rule-based" else NullEnhancer()
    requirement_by_id = {r.requirement_id: r for r in requirements}
    enhanced_cases = [
        enhancer.enhance(tc, requirement_by_id[tc.source_requirement_id]) for tc in test_cases
    ]

    output_path = export_test_cases(enhanced_cases, args.output)

    coverage_rows = build_traceability_report(requirements, enhanced_cases)
    report_text = format_report_as_text(coverage_rows)

    print(f"\nGenerated {len(enhanced_cases)} test case(s) from {len(requirements)} requirement(s).")
    print(f"Test cases written to: {output_path}")
    print("\nTraceability / coverage summary:")
    print(report_text)

    if args.report:
        report_path = export_traceability_report(coverage_rows, args.report)
        print(f"\nTraceability report written to: {report_path}")

    gap_count = sum(1 for row in coverage_rows if row.status == "NO_COVERAGE")
    if gap_count:
        print(f"\nWARNING: {gap_count} requirement(s) have NO generated test cases.")

    return 0


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    configure_logging(getattr(args, "log_level", "INFO"))

    try:
        if args.command == "generate":
            return run_generate(args)
        parser.error(f"Unknown command: {args.command}")
        return 2
    except RTCError as exc:
        logger.error(str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

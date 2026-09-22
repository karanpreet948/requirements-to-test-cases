"""Tests for rtc.traceability."""

from __future__ import annotations

import csv

from rtc.generator import TestCaseGenerator
from rtc.models import AcceptanceCriterion, Requirement
from rtc.traceability import build_traceability_report, export_traceability_report


def test_traceability_flags_zero_coverage_requirement(simple_requirement):
    uncovered_requirement = Requirement(
        requirement_id="REQ-NONE",
        title="Uncovered requirement",
        description="Has acceptance criteria but no generated test cases in this report.",
        acceptance_criteria=[AcceptanceCriterion(text="Given X, when Y, then Z.", index=1)],
    )

    generator = TestCaseGenerator()
    covered_cases = generator.generate_for_requirement(simple_requirement)
    # Intentionally do NOT generate cases for uncovered_requirement.

    rows = build_traceability_report(
        [simple_requirement, uncovered_requirement], covered_cases
    )

    rows_by_id = {row.requirement_id: row for row in rows}
    assert rows_by_id["REQ-NONE"].status == "NO_COVERAGE"
    assert rows_by_id["REQ-NONE"].test_case_count == 0
    assert rows_by_id[simple_requirement.requirement_id].status in {"OK", "LOW"}
    assert rows_by_id[simple_requirement.requirement_id].test_case_count == len(covered_cases)


def test_traceability_counts_by_type(simple_requirement):
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(simple_requirement)

    rows = build_traceability_report([simple_requirement], cases)
    row = rows[0]

    assert row.positive_count + row.negative_count + row.edge_count == row.test_case_count
    assert row.positive_count == len(simple_requirement.acceptance_criteria)


def test_export_traceability_report_writes_csv(tmp_path, simple_requirement):
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(simple_requirement)
    rows = build_traceability_report([simple_requirement], cases)

    output_path = tmp_path / "report.csv"
    export_traceability_report(rows, output_path)

    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as f:
        csv_rows = list(csv.reader(f))

    assert csv_rows[0][0] == "requirement_id"
    assert len(csv_rows) == 2  # header + 1 requirement row

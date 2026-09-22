"""Requirements-to-test-case traceability / coverage gap reporting.

A common BA/QA review question is: "which requirements have no test
coverage yet, and which ones might be over- or under-tested?" This module
builds a simple per-requirement coverage summary answering exactly that.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from rtc.models import Requirement, TestCase

logger = logging.getLogger(__name__)


@dataclass
class CoverageRow:
    """Test-case coverage summary for a single requirement."""

    requirement_id: str
    title: str
    acceptance_criteria_count: int
    test_case_count: int
    positive_count: int
    negative_count: int
    edge_count: int

    @property
    def status(self) -> str:
        """Human-readable coverage status: NO_COVERAGE / LOW / OK."""
        if self.test_case_count == 0:
            return "NO_COVERAGE"
        if self.test_case_count < self.acceptance_criteria_count:
            return "LOW"
        return "OK"


def build_traceability_report(
    requirements: List[Requirement], test_cases: List[TestCase]
) -> List[CoverageRow]:
    """Build one :class:`CoverageRow` per requirement.

    A requirement with zero generated test cases is flagged
    ``NO_COVERAGE``; one with fewer test cases than acceptance criteria is
    flagged ``LOW`` (a signal worth a human second look); otherwise ``OK``.
    """
    rows: List[CoverageRow] = []
    for requirement in requirements:
        related = [tc for tc in test_cases if tc.source_requirement_id == requirement.requirement_id]
        rows.append(
            CoverageRow(
                requirement_id=requirement.requirement_id,
                title=requirement.title,
                acceptance_criteria_count=len(requirement.acceptance_criteria),
                test_case_count=len(related),
                positive_count=sum(1 for tc in related if tc.type.value == "positive"),
                negative_count=sum(1 for tc in related if tc.type.value == "negative"),
                edge_count=sum(1 for tc in related if tc.type.value == "edge"),
            )
        )

    gap_count = sum(1 for row in rows if row.status == "NO_COVERAGE")
    if gap_count:
        logger.warning("%d requirement(s) have zero generated test cases", gap_count)
    else:
        logger.info("All requirements have at least one generated test case")

    return rows


def export_traceability_report(rows: List[CoverageRow], output_path: Union[str, Path]) -> Path:
    """Write the traceability report to a CSV file for easy review/sharing."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "requirement_id",
                "title",
                "acceptance_criteria_count",
                "test_case_count",
                "positive_count",
                "negative_count",
                "edge_count",
                "status",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.requirement_id,
                    row.title,
                    row.acceptance_criteria_count,
                    row.test_case_count,
                    row.positive_count,
                    row.negative_count,
                    row.edge_count,
                    row.status,
                ]
            )

    logger.info("Wrote traceability report to %s", path)
    return path


def format_report_as_text(rows: List[CoverageRow]) -> str:
    """Render the traceability report as a simple aligned text table,
    used for console/CLI output.
    """
    if not rows:
        return "(no requirements)"

    headers = ["Requirement", "Title", "AC#", "TestCases", "Pos", "Neg", "Edge", "Status"]
    data_rows = [
        [
            row.requirement_id,
            row.title[:32],
            str(row.acceptance_criteria_count),
            str(row.test_case_count),
            str(row.positive_count),
            str(row.negative_count),
            str(row.edge_count),
            row.status,
        ]
        for row in rows
    ]

    widths = [
        max(len(headers[i]), *(len(r[i]) for r in data_rows)) for i in range(len(headers))
    ]

    def _format_row(cells: List[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [_format_row(headers), _format_row(["-" * w for w in widths])]
    lines.extend(_format_row(r) for r in data_rows)
    return "\n".join(lines)

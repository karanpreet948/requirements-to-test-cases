"""Export generated test cases to Excel (.xlsx) or CSV.

Both export functions write the same column layout:

    test_case_id | source_requirement_id | type | title | preconditions |
    steps | expected_result

``steps`` is flattened to a single numbered, pipe-delimited string since
flat tabular formats cannot represent a nested list directly.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List, Union

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from rtc.exceptions import TestCaseExportError, UnsupportedFileFormatError
from rtc.models import TestCase

logger = logging.getLogger(__name__)

COLUMNS = [
    "test_case_id",
    "source_requirement_id",
    "type",
    "title",
    "preconditions",
    "steps",
    "expected_result",
]

_SUPPORTED_EXPORT_EXTENSIONS = {".xlsx", ".csv"}


def export_test_cases(test_cases: List[TestCase], output_path: Union[str, Path]) -> Path:
    """Export ``test_cases`` to ``output_path``, inferring format from extension.

    Parameters
    ----------
    test_cases:
        The test cases to export. May be empty (produces a header-only file).
    output_path:
        Destination path. Must end in ``.xlsx`` or ``.csv``.

    Returns
    -------
    Path
        The resolved path that was written.

    Raises
    ------
    UnsupportedFileFormatError
        If the output extension is not ``.xlsx`` or ``.csv``.
    TestCaseExportError
        If the file cannot be written (e.g. permissions, missing parent dir
        that cannot be created).
    """
    path = Path(output_path)
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_EXPORT_EXTENSIONS:
        raise UnsupportedFileFormatError(
            f"Unsupported export format '{suffix}'. Supported formats: "
            f"{sorted(_SUPPORTED_EXPORT_EXTENSIONS)}"
        )

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TestCaseExportError(f"Could not create output directory {path.parent}: {exc}") from exc

    if suffix == ".xlsx":
        _export_to_xlsx(test_cases, path)
    else:
        _export_to_csv(test_cases, path)

    logger.info("Exported %d test case(s) to %s", len(test_cases), path)
    return path


def _export_to_xlsx(test_cases: List[TestCase], path: Path) -> None:
    try:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Test Cases"

        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        for col_idx, column_name in enumerate(COLUMNS, start=1):
            cell = sheet.cell(row=1, column=col_idx, value=column_name)
            cell.font = header_font
            cell.fill = header_fill

        for row_idx, test_case in enumerate(test_cases, start=2):
            sheet.cell(row=row_idx, column=1, value=test_case.test_case_id)
            sheet.cell(row=row_idx, column=2, value=test_case.source_requirement_id)
            sheet.cell(row=row_idx, column=3, value=test_case.type.value)
            sheet.cell(row=row_idx, column=4, value=test_case.title)
            sheet.cell(row=row_idx, column=5, value=test_case.preconditions)
            sheet.cell(row=row_idx, column=6, value=test_case.steps_as_text())
            sheet.cell(row=row_idx, column=7, value=test_case.expected_result)

        _autosize_columns(sheet, num_columns=len(COLUMNS))
        sheet.freeze_panes = "A2"

        workbook.save(str(path))
    except OSError as exc:
        raise TestCaseExportError(f"Could not write Excel file to {path}: {exc}") from exc


def _autosize_columns(sheet, num_columns: int, max_width: int = 60) -> None:
    for col_idx in range(1, num_columns + 1):
        column_letter = get_column_letter(col_idx)
        longest = max(
            (len(str(cell.value)) for cell in sheet[column_letter] if cell.value is not None),
            default=10,
        )
        sheet.column_dimensions[column_letter].width = min(longest + 2, max_width)


def _export_to_csv(test_cases: List[TestCase], path: Path) -> None:
    try:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            for test_case in test_cases:
                writer.writerow(
                    [
                        test_case.test_case_id,
                        test_case.source_requirement_id,
                        test_case.type.value,
                        test_case.title,
                        test_case.preconditions,
                        test_case.steps_as_text(),
                        test_case.expected_result,
                    ]
                )
    except OSError as exc:
        raise TestCaseExportError(f"Could not write CSV file to {path}: {exc}") from exc

"""End-to-end tests for the CLI (rtc.cli.main)."""

from __future__ import annotations

import openpyxl
import pytest

from rtc.cli import main


def test_cli_generate_xlsx_end_to_end(tmp_path, sample_requirements_path, capsys):
    output_path = tmp_path / "test_cases.xlsx"
    report_path = tmp_path / "traceability.csv"

    exit_code = main(
        [
            "generate",
            "--input",
            str(sample_requirements_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert report_path.exists()

    workbook = openpyxl.load_workbook(output_path)
    sheet = workbook.active
    assert sheet.max_row > 1  # header + at least one test case

    captured = capsys.readouterr()
    assert "Generated" in captured.out
    assert "Traceability" in captured.out


def test_cli_generate_missing_input_file_returns_error(tmp_path, capsys):
    output_path = tmp_path / "test_cases.xlsx"
    exit_code = main(
        [
            "generate",
            "--input",
            str(tmp_path / "missing.yaml"),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error" in captured.err


def test_cli_generate_with_none_enhancer(tmp_path, sample_requirements_path):
    output_path = tmp_path / "test_cases.csv"
    exit_code = main(
        [
            "generate",
            "--input",
            str(sample_requirements_path),
            "--output",
            str(output_path),
            "--enhancer",
            "none",
        ]
    )
    assert exit_code == 0
    assert output_path.exists()

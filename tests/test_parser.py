"""Tests for rtc.parser."""

from __future__ import annotations

import json

import pytest

from rtc.exceptions import (
    RequirementFileNotFoundError,
    RequirementParseError,
    RequirementValidationError,
    UnsupportedFileFormatError,
)
from rtc.parser import load_requirements


def test_load_sample_requirements_succeeds(sample_requirements_path):
    requirements = load_requirements(sample_requirements_path)
    assert len(requirements) == 5
    first = requirements[0]
    assert first.requirement_id == "REQ-001"
    assert len(first.acceptance_criteria) == 3
    assert first.acceptance_criteria[0].index == 1


def test_load_requirements_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(RequirementFileNotFoundError):
        load_requirements(missing)


def test_load_requirements_unsupported_extension_raises(tmp_path):
    bad_file = tmp_path / "requirements.txt"
    bad_file.write_text("requirements: []")
    with pytest.raises(UnsupportedFileFormatError):
        load_requirements(bad_file)


def test_load_requirements_invalid_yaml_raises(tmp_path):
    bad_file = tmp_path / "broken.yaml"
    bad_file.write_text("requirements: [this is: not: valid: yaml")
    with pytest.raises(RequirementParseError):
        load_requirements(bad_file)


def test_load_requirements_missing_required_field_raises(tmp_path):
    bad_file = tmp_path / "missing_field.yaml"
    bad_file.write_text(
        "requirements:\n"
        "  - requirement_id: REQ-999\n"
        "    title: Missing description and criteria\n"
    )
    with pytest.raises(RequirementValidationError):
        load_requirements(bad_file)


def test_load_requirements_empty_list_raises(tmp_path):
    bad_file = tmp_path / "empty.yaml"
    bad_file.write_text("requirements: []")
    with pytest.raises(RequirementValidationError):
        load_requirements(bad_file)


def test_load_requirements_accepts_bare_list_json(tmp_path):
    data = [
        {
            "requirement_id": "REQ-JSON-1",
            "title": "JSON requirement",
            "description": "A requirement provided as a bare JSON list.",
            "acceptance_criteria": ["Given X, when Y, then Z."],
        }
    ]
    json_file = tmp_path / "requirements.json"
    json_file.write_text(json.dumps(data))

    requirements = load_requirements(json_file)
    assert len(requirements) == 1
    assert requirements[0].requirement_id == "REQ-JSON-1"


def test_load_requirements_empty_acceptance_criteria_raises(tmp_path):
    bad_file = tmp_path / "empty_ac.yaml"
    bad_file.write_text(
        "requirements:\n"
        "  - requirement_id: REQ-1\n"
        "    title: T\n"
        "    description: D\n"
        "    acceptance_criteria: []\n"
    )
    with pytest.raises(RequirementValidationError):
        load_requirements(bad_file)

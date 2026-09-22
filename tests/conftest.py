"""Shared pytest fixtures for the rtc test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from rtc.models import AcceptanceCriterion, Requirement

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_REQUIREMENTS_PATH = REPO_ROOT / "examples" / "sample_requirements.yaml"


@pytest.fixture
def sample_requirements_path() -> Path:
    return SAMPLE_REQUIREMENTS_PATH


@pytest.fixture
def simple_requirement() -> Requirement:
    return Requirement(
        requirement_id="REQ-100",
        title="Test requirement",
        description="A requirement used purely for unit testing.",
        acceptance_criteria=[
            AcceptanceCriterion(
                text=(
                    "Given a user is on the form, when they enter a value that "
                    "is at least the minimum of 5 and at most the maximum of 10, "
                    "then the value is accepted."
                ),
                index=1,
            ),
            AcceptanceCriterion(
                text=(
                    "Given a user is on the form, the field is required, so when "
                    "they submit without it, then a validation error is shown."
                ),
                index=2,
            ),
        ],
    )

"""Core data structures shared across the rtc package.

These are intentionally plain ``dataclasses`` (no ORM, no pydantic
dependency) so the package stays lightweight and easy to read for a BA
audience reviewing the source as a portfolio artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class TestCaseType(str, Enum):
    """Classification of a generated test case."""

    __test__ = False  # tell pytest this is not a test class to collect

    POSITIVE = "positive"
    NEGATIVE = "negative"
    EDGE = "edge"


@dataclass
class AcceptanceCriterion:
    """A single acceptance criterion belonging to a requirement.

    Attributes
    ----------
    text:
        The raw acceptance criterion text, typically written in
        Given/When/Then style, e.g.
        ``"Given a returning customer, when they enter a valid loyalty
        number, then the discount is applied at checkout."``
    index:
        1-based position of this criterion within its requirement's
        acceptance_criteria list. Used to build stable, human-readable
        test case IDs.
    """

    text: str
    index: int


@dataclass
class Requirement:
    """A single business requirement (user story) with acceptance criteria."""

    requirement_id: str
    title: str
    description: str
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)


@dataclass
class TestCase:
    """A single draft QA test case generated from an acceptance criterion."""

    test_case_id: str
    source_requirement_id: str
    title: str
    preconditions: str
    steps: List[str]
    expected_result: str
    type: TestCaseType

    def steps_as_text(self, separator: str = " | ") -> str:
        """Render the ordered steps list as a single delimited string.

        Useful for flat export formats (CSV/Excel cells) where a list
        cannot be stored directly.
        """
        return separator.join(f"{i}. {s}" for i, s in enumerate(self.steps, start=1))

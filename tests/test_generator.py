"""Tests for rtc.generator."""

from __future__ import annotations

from rtc.generator import TestCaseGenerator
from rtc.models import TestCaseType


def test_generate_for_requirement_always_includes_positive_case(simple_requirement):
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(simple_requirement)

    positive_cases = [c for c in cases if c.type == TestCaseType.POSITIVE]
    assert len(positive_cases) == len(simple_requirement.acceptance_criteria)


def test_generate_detects_minimum_and_maximum_keywords(simple_requirement):
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(simple_requirement)

    edge_ids = {c.test_case_id for c in cases if c.type == TestCaseType.EDGE}
    assert any("EDGE-MIN" in cid for cid in edge_ids)
    assert any("EDGE-MAX" in cid for cid in edge_ids)


def test_generate_detects_required_keyword(simple_requirement):
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(simple_requirement)

    negative_ids = {c.test_case_id for c in cases if c.type == TestCaseType.NEGATIVE}
    assert any("NEG-REQ" in cid for cid in negative_ids)


def test_generate_ids_are_unique_and_traceable(simple_requirement):
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(simple_requirement)

    ids = [c.test_case_id for c in cases]
    assert len(ids) == len(set(ids)), "test_case_id values must be unique"
    for case in cases:
        assert case.source_requirement_id == simple_requirement.requirement_id
        assert simple_requirement.requirement_id in case.test_case_id


def test_generate_produces_generic_negative_when_no_keywords_match():
    from rtc.models import AcceptanceCriterion, Requirement

    requirement = Requirement(
        requirement_id="REQ-200",
        title="Plain requirement",
        description="No special keywords here.",
        acceptance_criteria=[
            AcceptanceCriterion(
                text="Given the user is logged in, when they view the dashboard, then it loads.",
                index=1,
            )
        ],
    )
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(requirement)

    assert len(cases) == 2  # one positive + one generic negative
    types = {c.type for c in cases}
    assert types == {TestCaseType.POSITIVE, TestCaseType.NEGATIVE}


def test_generate_handles_plain_non_gwt_text():
    from rtc.models import AcceptanceCriterion, Requirement

    requirement = Requirement(
        requirement_id="REQ-201",
        title="Non-GWT requirement",
        description="Acceptance criterion not written in Given/When/Then form.",
        acceptance_criteria=[
            AcceptanceCriterion(text="The system must log every login attempt.", index=1)
        ],
    )
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(requirement)

    assert len(cases) >= 2
    for case in cases:
        assert case.title
        assert case.expected_result
        assert case.steps


def test_generate_for_full_requirement_list(sample_requirements_path):
    from rtc.parser import load_requirements

    requirements = load_requirements(sample_requirements_path)
    generator = TestCaseGenerator()
    all_cases = generator.generate(requirements)

    # Every requirement should have generated at least one test case.
    covered_ids = {c.source_requirement_id for c in all_cases}
    for requirement in requirements:
        assert requirement.requirement_id in covered_ids

    # Every acceptance criterion produces at least a positive case, so the
    # total should be at least the number of acceptance criteria.
    total_criteria = sum(len(r.acceptance_criteria) for r in requirements)
    assert len(all_cases) >= total_criteria

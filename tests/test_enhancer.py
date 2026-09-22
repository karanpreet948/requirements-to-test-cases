"""Tests for rtc.enhancer."""

from __future__ import annotations

from rtc.enhancer import NullEnhancer, RuleBasedEnhancer
from rtc.generator import TestCaseGenerator
from rtc.models import AcceptanceCriterion, Requirement


def test_null_enhancer_returns_same_test_case(simple_requirement):
    generator = TestCaseGenerator()
    cases = generator.generate_for_requirement(simple_requirement)
    enhancer = NullEnhancer()

    for case in cases:
        result = enhancer.enhance(case, simple_requirement)
        assert result is case


def test_rule_based_enhancer_tidies_whitespace_and_capitalization():
    requirement = Requirement(
        requirement_id="REQ-300",
        title="Email capture",
        description="Applicant email is collected during onboarding.",
        acceptance_criteria=[
            AcceptanceCriterion(text="given a user, when they enter email, then it is saved.", index=1)
        ],
    )
    generator = TestCaseGenerator()
    case = generator.generate_for_requirement(requirement)[0]

    # Introduce messy whitespace to confirm tidy-up behavior.
    case.preconditions = "the   system   is ready"

    enhancer = RuleBasedEnhancer()
    enhanced = enhancer.enhance(case, requirement)

    assert "  " not in enhanced.preconditions
    assert enhanced.preconditions[0].isupper()


def test_rule_based_enhancer_adds_sample_data_hint_for_known_fields():
    requirement = Requirement(
        requirement_id="REQ-301",
        title="Email capture",
        description="Applicant provides an email address during onboarding.",
        acceptance_criteria=[
            AcceptanceCriterion(
                text="Given a user, when they enter a valid email, then it is saved.", index=1
            )
        ],
    )
    generator = TestCaseGenerator()
    case = generator.generate_for_requirement(requirement)[0]

    enhancer = RuleBasedEnhancer()
    enhanced = enhancer.enhance(case, requirement)

    assert any("email" in step.lower() and "@" in step for step in enhanced.steps)

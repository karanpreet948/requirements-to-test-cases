"""Pluggable "enhancer" interface for refining draft test case wording.

Why this exists
----------------
The :mod:`rtc.generator` module produces *mechanically correct but plainly
worded* draft test cases from simple keyword rules. In a real-world
workflow, a Business Analyst would often want to run those drafts through
a Large Language Model (e.g. ChatGPT, Copilot, an internal LLM gateway) to:

- smooth out awkward auto-generated phrasing,
- add realistic sample data,
- suggest additional edge cases the rules missed,
- align tone/terminology with a house style guide.

This module defines the seam where that integration would happen, via the
:class:`TestCaseEnhancer` abstract base class. This portfolio project ships
only a concrete **local, rule-based** implementation
(:class:`RuleBasedEnhancer`) that runs fully offline with no network calls
and no API key — it just tidies up phrasing and fills in a couple of
plausible sample values using simple string templates.

Plugging in a real LLM
-----------------------
A production integration would add a new subclass, e.g.::

    class OpenAIEnhancer(TestCaseEnhancer):
        def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
            self._client = SomeLLMClient(api_key=api_key)
            self._model = model

        def enhance(self, test_case: TestCase, requirement: Requirement) -> TestCase:
            prompt = build_prompt(test_case, requirement)
            response = self._client.complete(model=self._model, prompt=prompt)
            return apply_llm_suggestions(test_case, response)

The API key would be read from an environment variable (see
``config/.env.example``) — never hard-coded or committed to source control.
That subclass is intentionally NOT implemented here, to keep this
repository runnable fully offline with zero external dependencies or
secrets.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from rtc.models import Requirement, TestCase

logger = logging.getLogger(__name__)


class TestCaseEnhancer(ABC):
    """Abstract interface for a component that refines a draft test case.

    Implementations receive the originating :class:`~rtc.models.Requirement`
    for context (e.g. to reference domain terms from its title/description)
    alongside the draft :class:`~rtc.models.TestCase` to improve.
    """

    @abstractmethod
    def enhance(self, test_case: TestCase, requirement: Requirement) -> TestCase:
        """Return an improved copy of ``test_case``.

        Implementations should not mutate the input in place; they should
        return a new :class:`~rtc.models.TestCase` instance (or the same
        instance if no change was made) so callers can compare before/after
        if desired.
        """
        raise NotImplementedError


class NullEnhancer(TestCaseEnhancer):
    """A no-op enhancer. Useful as an explicit "skip enhancement" choice."""

    def enhance(self, test_case: TestCase, requirement: Requirement) -> TestCase:
        return test_case


class RuleBasedEnhancer(TestCaseEnhancer):
    """A simple, fully offline, template-based enhancer.

    This is NOT a machine-learning model. It applies a handful of
    deterministic text-cleanup rules that a real LLM-backed enhancer would
    also do (and do more thoroughly):

    - collapse duplicated whitespace,
    - ensure titles are capitalized and free of double punctuation,
    - append a short, generic sample-data hint for common field names found
      in the requirement's title/description, so a QA engineer has a
      concrete example value to start from.
    """

    #: very small "field name" -> "example value" lookup used to enrich
    #: steps with a plausible sample value when the field is mentioned.
    _SAMPLE_VALUES = {
        "email": "jane.doe@example.com",
        "phone": "555-0100",
        "date of birth": "1990-05-14",
        "loyalty number": "LOY-000123",
        "account number": "ACC-000456",
        "postal code": "94105",
        "zip code": "94105",
        "amount": "1,250.00",
        "income": "62,000.00",
    }

    def enhance(self, test_case: TestCase, requirement: Requirement) -> TestCase:
        title = self._tidy_text(test_case.title)
        preconditions = self._tidy_text(test_case.preconditions)
        steps = [self._tidy_text(step) for step in test_case.steps]
        expected_result = self._tidy_text(test_case.expected_result)

        sample_hint = self._find_sample_hint(requirement)
        if sample_hint:
            steps = steps + [f"(Suggested sample data: {sample_hint})"]

        enhanced = TestCase(
            test_case_id=test_case.test_case_id,
            source_requirement_id=test_case.source_requirement_id,
            title=title,
            preconditions=preconditions,
            steps=steps,
            expected_result=expected_result,
            type=test_case.type,
        )
        logger.debug("Enhanced test case %s", test_case.test_case_id)
        return enhanced

    @staticmethod
    def _tidy_text(text: str) -> str:
        if not text:
            return text
        collapsed = re.sub(r"\s+", " ", text).strip()
        collapsed = re.sub(r"\.{2,}$", ".", collapsed)
        if collapsed and not collapsed[0].isupper():
            collapsed = collapsed[0].upper() + collapsed[1:]
        return collapsed

    def _find_sample_hint(self, requirement: Requirement) -> str:
        haystack = f"{requirement.title} {requirement.description}".lower()
        for field_name, example_value in self._SAMPLE_VALUES.items():
            if field_name in haystack:
                return f"{field_name} = {example_value}"
        return ""

"""Rule-based generation of draft test cases from acceptance criteria.

This module intentionally uses simple, transparent, rule-based heuristics
(keyword matching + light text transformation) rather than any machine
learning or external API. The goal is a *first draft scaffold* that a human
QA engineer or BA reviews and refines — see :mod:`rtc.enhancer` for the
pluggable point where a real LLM could take over that refinement step.

Heuristics implemented
-----------------------
1. Every acceptance criterion always yields one POSITIVE test case that
   walks the literal Given/When/Then path.
2. Keyword-triggered NEGATIVE/EDGE cases are added on top of that, based on
   words commonly found in acceptance criteria:
   - "required" / "must provide" / "mandatory"  -> negative: field omitted
   - "valid" / "correct"                         -> negative: invalid input
   - "at least" / "minimum" / "no less than"     -> edge: below-minimum boundary
   - "maximum" / "at most" / "no more than"      -> edge: above-maximum boundary
   - "unique"                                    -> negative: duplicate value
   - none of the above matched                   -> generic negative: negated condition
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable, List

from rtc.models import AcceptanceCriterion, Requirement, TestCase, TestCaseType

logger = logging.getLogger(__name__)

_GWT_PATTERN = re.compile(
    r"^\s*given\s+(?P<given>.*?)\s*,?\s*when\s+(?P<when>.*?)\s*,?\s*then\s+(?P<then>.*?)\s*$",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class _GwtParts:
    """Parsed Given/When/Then components of an acceptance criterion."""

    given: str
    when: str
    then: str
    is_structured: bool  # True if the text actually matched Given/When/Then form


def _parse_gwt(text: str) -> _GwtParts:
    """Best-effort split of free text into Given/When/Then parts.

    Falls back gracefully to treating the whole string as the "when"/action
    clause if it is not written in strict Given/When/Then form, so the
    generator still works on plain acceptance-criteria sentences.
    """
    match = _GWT_PATTERN.match(text)
    if match:
        return _GwtParts(
            given=match.group("given").strip() or "the system is in its default state",
            when=match.group("when").strip(),
            then=match.group("then").strip(),
            is_structured=True,
        )
    return _GwtParts(
        given="the system is in its default state",
        when=text.strip().rstrip("."),
        then="the system behaves as described in the acceptance criterion",
        is_structured=False,
    )


class TestCaseGenerator:
    """Generates draft test cases for a list of requirements.

    Parameters
    ----------
    id_prefix:
        Prefix used when building test_case_id values, e.g. ``"TC"`` yields
        IDs like ``TC-REQ-001-AC1-POS``.
    """

    #: Tells pytest this is not a test class to collect, despite the name.
    __test__ = False

    def __init__(self, id_prefix: str = "TC") -> None:
        self.id_prefix = id_prefix
        # Ordered list of (keyword predicate, case-builder) pairs. The first
        # matching keyword rule fires; if none match, a generic negative
        # case is generated instead. Order matters: more specific keyword
        # groups are checked before the generic fallback.
        self._keyword_rules: List[
            "tuple[Callable[[str], bool], Callable[[Requirement, AcceptanceCriterion, _GwtParts], TestCase]]"
        ] = [
            (self._mentions_required, self._build_missing_required_case),
            (self._mentions_minimum, self._build_below_minimum_case),
            (self._mentions_maximum, self._build_above_maximum_case),
            (self._mentions_unique, self._build_duplicate_value_case),
            (self._mentions_valid, self._build_invalid_input_case),
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_for_requirement(self, requirement: Requirement) -> List[TestCase]:
        """Generate all draft test cases for a single requirement."""
        test_cases: List[TestCase] = []
        for criterion in requirement.acceptance_criteria:
            test_cases.extend(self._generate_for_criterion(requirement, criterion))
        logger.debug(
            "Generated %d test case(s) for requirement %s",
            len(test_cases),
            requirement.requirement_id,
        )
        return test_cases

    def generate(self, requirements: List[Requirement]) -> List[TestCase]:
        """Generate draft test cases for every requirement in ``requirements``."""
        all_cases: List[TestCase] = []
        for requirement in requirements:
            all_cases.extend(self.generate_for_requirement(requirement))
        logger.info(
            "Generated %d total test case(s) across %d requirement(s)",
            len(all_cases),
            len(requirements),
        )
        return all_cases

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _generate_for_criterion(
        self, requirement: Requirement, criterion: AcceptanceCriterion
    ) -> List[TestCase]:
        gwt = _parse_gwt(criterion.text)
        cases = [self._build_positive_case(requirement, criterion, gwt)]

        matched_any = False
        text_lower = criterion.text.lower()
        for predicate, builder in self._keyword_rules:
            if predicate(text_lower):
                cases.append(builder(requirement, criterion, gwt))
                matched_any = True

        if not matched_any:
            cases.append(self._build_generic_negative_case(requirement, criterion, gwt))

        return cases

    def _make_id(self, requirement: Requirement, criterion: AcceptanceCriterion, suffix: str) -> str:
        return f"{self.id_prefix}-{requirement.requirement_id}-AC{criterion.index}-{suffix}"

    # -- keyword predicates -------------------------------------------------

    @staticmethod
    def _mentions_required(text_lower: str) -> bool:
        return any(kw in text_lower for kw in ("required", "must provide", "mandatory"))

    @staticmethod
    def _mentions_minimum(text_lower: str) -> bool:
        return any(kw in text_lower for kw in ("at least", "minimum", "no less than"))

    @staticmethod
    def _mentions_maximum(text_lower: str) -> bool:
        return any(kw in text_lower for kw in ("maximum", "at most", "no more than"))

    @staticmethod
    def _mentions_unique(text_lower: str) -> bool:
        return "unique" in text_lower

    @staticmethod
    def _mentions_valid(text_lower: str) -> bool:
        return any(kw in text_lower for kw in ("valid ", "correct "))

    # -- case builders --------------------------------------------------

    def _build_positive_case(
        self, requirement: Requirement, criterion: AcceptanceCriterion, gwt: _GwtParts
    ) -> TestCase:
        return TestCase(
            test_case_id=self._make_id(requirement, criterion, "POS"),
            source_requirement_id=requirement.requirement_id,
            title=f"Verify: {gwt.when or criterion.text}"[:120],
            preconditions=gwt.given,
            steps=[
                f"Set up the system so that: {gwt.given}.",
                f"Perform the action: {gwt.when}.",
            ],
            expected_result=f"The system confirms that {gwt.then}.",
            type=TestCaseType.POSITIVE,
        )

    def _build_generic_negative_case(
        self, requirement: Requirement, criterion: AcceptanceCriterion, gwt: _GwtParts
    ) -> TestCase:
        negated_when = self._negate(gwt.when)
        return TestCase(
            test_case_id=self._make_id(requirement, criterion, "NEG"),
            source_requirement_id=requirement.requirement_id,
            title=f"Verify rejection when: {negated_when}"[:120],
            preconditions=gwt.given,
            steps=[
                f"Set up the system so that: {gwt.given}.",
                f"Perform the action, but with the condition inverted: {negated_when}.",
            ],
            expected_result=(
                f"The system does NOT confirm that {gwt.then}; an appropriate "
                "validation message or alternate flow is shown instead."
            ),
            type=TestCaseType.NEGATIVE,
        )

    def _build_missing_required_case(
        self, requirement: Requirement, criterion: AcceptanceCriterion, gwt: _GwtParts
    ) -> TestCase:
        return TestCase(
            test_case_id=self._make_id(requirement, criterion, "NEG-REQ"),
            source_requirement_id=requirement.requirement_id,
            title=f"Verify error when required data is missing ({requirement.title})"[:120],
            preconditions=gwt.given,
            steps=[
                f"Set up the system so that: {gwt.given}.",
                f"Attempt to perform the action while omitting a required field: {gwt.when}.",
            ],
            expected_result=(
                "The system blocks the action and displays a validation error "
                "indicating that the required field must be provided."
            ),
            type=TestCaseType.NEGATIVE,
        )

    def _build_below_minimum_case(
        self, requirement: Requirement, criterion: AcceptanceCriterion, gwt: _GwtParts
    ) -> TestCase:
        return TestCase(
            test_case_id=self._make_id(requirement, criterion, "EDGE-MIN"),
            source_requirement_id=requirement.requirement_id,
            title=f"Verify boundary just below the minimum ({requirement.title})"[:120],
            preconditions=gwt.given,
            steps=[
                f"Set up the system so that: {gwt.given}.",
                f"Perform the action using a value one unit below the stated minimum: {gwt.when}.",
            ],
            expected_result=(
                "The system rejects the value and displays a message stating the "
                "minimum requirement, without completing the action."
            ),
            type=TestCaseType.EDGE,
        )

    def _build_above_maximum_case(
        self, requirement: Requirement, criterion: AcceptanceCriterion, gwt: _GwtParts
    ) -> TestCase:
        return TestCase(
            test_case_id=self._make_id(requirement, criterion, "EDGE-MAX"),
            source_requirement_id=requirement.requirement_id,
            title=f"Verify boundary just above the maximum ({requirement.title})"[:120],
            preconditions=gwt.given,
            steps=[
                f"Set up the system so that: {gwt.given}.",
                f"Perform the action using a value one unit above the stated maximum: {gwt.when}.",
            ],
            expected_result=(
                "The system rejects the value and displays a message stating the "
                "maximum allowed, without completing the action."
            ),
            type=TestCaseType.EDGE,
        )

    def _build_duplicate_value_case(
        self, requirement: Requirement, criterion: AcceptanceCriterion, gwt: _GwtParts
    ) -> TestCase:
        return TestCase(
            test_case_id=self._make_id(requirement, criterion, "NEG-DUP"),
            source_requirement_id=requirement.requirement_id,
            title=f"Verify rejection of a duplicate value ({requirement.title})"[:120],
            preconditions=gwt.given,
            steps=[
                f"Set up the system so that: {gwt.given}, and a matching value already exists.",
                f"Attempt to perform the action using the same, already-existing value: {gwt.when}.",
            ],
            expected_result=(
                "The system rejects the duplicate and displays a uniqueness "
                "validation error."
            ),
            type=TestCaseType.NEGATIVE,
        )

    def _build_invalid_input_case(
        self, requirement: Requirement, criterion: AcceptanceCriterion, gwt: _GwtParts
    ) -> TestCase:
        return TestCase(
            test_case_id=self._make_id(requirement, criterion, "NEG-INV"),
            source_requirement_id=requirement.requirement_id,
            title=f"Verify rejection of invalid input ({requirement.title})"[:120],
            preconditions=gwt.given,
            steps=[
                f"Set up the system so that: {gwt.given}.",
                f"Perform the action using a clearly invalid/malformed value: {gwt.when}.",
            ],
            expected_result=(
                "The system rejects the invalid input and displays a clear "
                "validation error message, without completing the action."
            ),
            type=TestCaseType.NEGATIVE,
        )

    # -- text helpers -----------------------------------------------------

    @staticmethod
    def _negate(clause: str) -> str:
        """Very small, heuristic negation of a when-clause for generic
        negative test titles. Not linguistically perfect by design — this
        is a draft-generation aid, reviewed by a human, not a grammar engine.
        """
        clause = clause.strip()
        if not clause:
            return "the described action does not occur"
        lowered = clause.lower()
        if lowered.startswith("the user "):
            return "the user does NOT " + clause[len("the user "):]
        if " is " in clause:
            return clause.replace(" is ", " is NOT ", 1)
        if " has " in clause:
            return clause.replace(" has ", " does NOT have ", 1)
        return f"the following does NOT occur: {clause}"

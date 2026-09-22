"""
rtc — Requirements-to-Test-Cases
=================================

A small, offline toolkit that helps Business Analysts and QA engineers turn
structured requirements (user stories + acceptance criteria) into draft QA
test cases, with full traceability back to the originating requirement.

This package is a portfolio / demonstration project. All data used with it
is synthetic and fictional.

Public API
----------
- :mod:`rtc.models` — data classes for Requirement, AcceptanceCriterion, TestCase
- :mod:`rtc.parser` — load and validate requirements from YAML/JSON
- :mod:`rtc.generator` — rule-based test case generation
- :mod:`rtc.enhancer` — pluggable enhancer interface + a local rule-based enhancer
- :mod:`rtc.exporter` — Excel/CSV export of generated test cases
- :mod:`rtc.traceability` — coverage / traceability reporting
- :mod:`rtc.cli` — command line interface (``python -m rtc``)
"""

__version__ = "1.0.0"

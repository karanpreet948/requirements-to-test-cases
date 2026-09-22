"""Custom exception hierarchy for the rtc package.

Using specific exception types (instead of bare ``except: pass`` or generic
``Exception``) makes failures explicit and actionable for callers, both when
this package is used as a library and when it is driven from the CLI.
"""

from __future__ import annotations


class RTCError(Exception):
    """Base class for all errors raised intentionally by the rtc package."""


class RequirementFileNotFoundError(RTCError):
    """Raised when the requirements input file does not exist on disk."""


class UnsupportedFileFormatError(RTCError):
    """Raised when the input/output file extension is not supported.

    Supported requirement input formats: ``.yaml``, ``.yml``, ``.json``.
    Supported test-case export formats: ``.xlsx``, ``.csv``.
    """


class RequirementParseError(RTCError):
    """Raised when a requirements file cannot be parsed as valid YAML/JSON."""


class RequirementValidationError(RTCError):
    """Raised when parsed requirement data is missing required fields or is
    otherwise structurally invalid (e.g. wrong types, empty required lists).
    """


class TestCaseExportError(RTCError):
    """Raised when generated test cases cannot be written to the requested
    output file (e.g. unwritable path, unsupported format).
    """

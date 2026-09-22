"""Parsing and validation of requirements input files (YAML or JSON).

Expected input shape (YAML shown, JSON is structurally identical)::

    requirements:
      - requirement_id: REQ-001
        title: Short title
        description: Longer free-text description
        acceptance_criteria:
          - "Given ... when ... then ..."
          - "Given ... when ... then ..."

A bare top-level list (without the ``requirements:`` wrapper key) is also
accepted for convenience.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

from rtc.exceptions import (
    RequirementFileNotFoundError,
    RequirementParseError,
    RequirementValidationError,
    UnsupportedFileFormatError,
)
from rtc.models import AcceptanceCriterion, Requirement

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".yaml", ".yml", ".json"}
_REQUIRED_FIELDS = ("requirement_id", "title", "description", "acceptance_criteria")


def load_requirements(path: Union[str, Path]) -> List[Requirement]:
    """Load, parse, and validate requirements from a YAML or JSON file.

    Parameters
    ----------
    path:
        Path to a ``.yaml``, ``.yml``, or ``.json`` file.

    Returns
    -------
    list of :class:`rtc.models.Requirement`

    Raises
    ------
    RequirementFileNotFoundError
        If ``path`` does not exist.
    UnsupportedFileFormatError
        If the file extension is not one of the supported formats.
    RequirementParseError
        If the file content is not valid YAML/JSON.
    RequirementValidationError
        If the parsed content does not match the expected requirement schema.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise RequirementFileNotFoundError(f"Requirements file not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        raise UnsupportedFileFormatError(
            f"Unsupported requirements file format '{suffix}'. "
            f"Supported formats: {sorted(_SUPPORTED_EXTENSIONS)}"
        )

    raw_text = file_path.read_text(encoding="utf-8")
    logger.debug("Read %d bytes from %s", len(raw_text), file_path)

    data = _parse_raw_text(raw_text, suffix, file_path)
    requirement_dicts = _extract_requirement_list(data, file_path)

    requirements = [
        _build_requirement(item, position=i, source=file_path)
        for i, item in enumerate(requirement_dicts)
    ]

    logger.info("Loaded %d requirement(s) from %s", len(requirements), file_path)
    return requirements


def _parse_raw_text(raw_text: str, suffix: str, file_path: Path) -> Any:
    try:
        if suffix == ".json":
            return json.loads(raw_text)
        return yaml.safe_load(raw_text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise RequirementParseError(
            f"Could not parse {file_path} as valid {'JSON' if suffix == '.json' else 'YAML'}: {exc}"
        ) from exc


def _extract_requirement_list(data: Any, file_path: Path) -> List[Dict[str, Any]]:
    if data is None:
        raise RequirementValidationError(f"{file_path} is empty; expected requirement data.")

    if isinstance(data, dict) and "requirements" in data:
        candidate = data["requirements"]
    else:
        candidate = data

    if not isinstance(candidate, list):
        raise RequirementValidationError(
            f"{file_path} must contain a list of requirements "
            "(either at the top level, or under a 'requirements' key)."
        )

    if len(candidate) == 0:
        raise RequirementValidationError(f"{file_path} contains zero requirements.")

    return candidate


def _build_requirement(item: Any, position: int, source: Path) -> Requirement:
    if not isinstance(item, dict):
        raise RequirementValidationError(
            f"Requirement at position {position} in {source} must be a mapping/object, "
            f"got {type(item).__name__}."
        )

    missing = [f for f in _REQUIRED_FIELDS if f not in item]
    if missing:
        raise RequirementValidationError(
            f"Requirement at position {position} in {source} is missing required "
            f"field(s): {missing}"
        )

    requirement_id = str(item["requirement_id"]).strip()
    title = str(item["title"]).strip()
    description = str(item["description"]).strip()
    raw_criteria = item["acceptance_criteria"]

    if not requirement_id:
        raise RequirementValidationError(
            f"Requirement at position {position} in {source} has an empty requirement_id."
        )

    if not isinstance(raw_criteria, list) or len(raw_criteria) == 0:
        raise RequirementValidationError(
            f"Requirement '{requirement_id}' must have a non-empty list of "
            "acceptance_criteria."
        )

    criteria = []
    for idx, criterion_text in enumerate(raw_criteria, start=1):
        text = str(criterion_text).strip()
        if not text:
            raise RequirementValidationError(
                f"Requirement '{requirement_id}' has an empty acceptance criterion "
                f"at position {idx}."
            )
        criteria.append(AcceptanceCriterion(text=text, index=idx))

    return Requirement(
        requirement_id=requirement_id,
        title=title,
        description=description,
        acceptance_criteria=criteria,
    )

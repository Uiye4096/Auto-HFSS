"""Configuration models for reusable HFSS batch execution.

The module intentionally uses only the Python standard library so it can be
used on research workstations without an additional dependency bootstrap.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class HFSSConfig:
    aedt_root: Path
    ironpython: Path
    non_graphical: bool = True
    max_parallel: int = 1


@dataclass(frozen=True)
class ProjectConfig:
    project_file: Path
    design: str
    setup: str
    sweep: str
    ports: int
    output_root: Path
    variables: Mapping[str, str]


@dataclass(frozen=True)
class AutomationConfig:
    hfss: HFSSConfig
    project: ProjectConfig


def _require(mapping: Mapping[str, Any], key: str, section: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Missing required configuration key: {section}.{key}")
    return mapping[key]


def _path(value: Any, base_dir: Path) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(str(value))))
    return path if path.is_absolute() else (base_dir / path).resolve()


def _positive_int(value: Any, name: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def load_config(path: str | Path, env: Optional[Mapping[str, str]] = None) -> AutomationConfig:
    """Load and validate a JSON configuration file.

    Environment variables can override machine-specific HFSS paths:

    - ``HFSS_AEDT_ROOT``
    - ``HFSS_IRONPYTHON``
    - ``HFSS_MAX_PARALLEL``
    """

    config_path = Path(path).expanduser().resolve()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Top-level configuration must be a JSON object")

    env_values = dict(os.environ if env is None else env)
    base_dir = config_path.parent
    hfss_raw: Dict[str, Any] = dict(_require(raw, "hfss", "root"))
    project_raw: Dict[str, Any] = dict(_require(raw, "project", "root"))

    aedt_root_value = env_values.get("HFSS_AEDT_ROOT", _require(hfss_raw, "aedt_root", "hfss"))
    ironpython_value = env_values.get("HFSS_IRONPYTHON", _require(hfss_raw, "ironpython", "hfss"))
    max_parallel_value = env_values.get("HFSS_MAX_PARALLEL", hfss_raw.get("max_parallel", 1))

    variables = project_raw.get("variables", {})
    if not isinstance(variables, dict):
        raise ValueError("project.variables must be a JSON object")

    hfss = HFSSConfig(
        aedt_root=_path(aedt_root_value, base_dir),
        ironpython=_path(ironpython_value, base_dir),
        non_graphical=bool(hfss_raw.get("non_graphical", True)),
        max_parallel=_positive_int(max_parallel_value, "hfss.max_parallel"),
    )
    project = ProjectConfig(
        project_file=_path(_require(project_raw, "project_file", "project"), base_dir),
        design=str(_require(project_raw, "design", "project")),
        setup=str(_require(project_raw, "setup", "project")),
        sweep=str(_require(project_raw, "sweep", "project")),
        ports=_positive_int(_require(project_raw, "ports", "project"), "project.ports"),
        output_root=_path(project_raw.get("output_root", "runs"), base_dir),
        variables={str(key): str(value) for key, value in variables.items()},
    )

    return AutomationConfig(hfss=hfss, project=project)

"""Configuration-driven entry point for one reproducible HFSS run.

This CLI does not replace the existing diplexer workflow. It provides a
project-independent path that copies a baseline AEDT project, applies optional
variable updates, invokes the generic IronPython runner, and records provenance.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from hfss_automation.config import AutomationConfig, load_config


REPO_ROOT = Path(__file__).resolve().parent
INSPECTOR = REPO_ROOT / "tools" / "aedt_inspect.py"
GENERIC_RUNNER = REPO_ROOT / "scripts" / "run_hfss_generic.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one HFSS case from JSON configuration.")
    parser.add_argument("config", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Prepare the case without launching HFSS")
    parser.add_argument("--case-name", help="Optional stable case directory name")
    return parser.parse_args()


def build_runner_command(config: AutomationConfig, project_path: Path, output_dir: Path) -> List[str]:
    return [
        str(config.hfss.ironpython),
        str(GENERIC_RUNNER),
        str(project_path),
        str(output_dir),
        "--aedt-root",
        str(config.hfss.aedt_root),
        "--design",
        config.project.design,
        "--setup",
        config.project.setup,
        "--sweep",
        config.project.sweep,
        "--ports",
        str(config.project.ports),
    ]


def apply_updates(source: Path, destination: Path, updates: dict[str, str], case_dir: Path) -> None:
    if not updates:
        shutil.copy2(source, destination)
        return

    updates_path = case_dir / "updates.json"
    result_path = case_dir / "update_result.json"
    updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(INSPECTOR),
            str(source),
            "--set",
            str(updates_path),
            "--write-to",
            str(destination),
            "--out",
            str(result_path),
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "AEDT variable update failed:\n{}".format(completed.stderr or completed.stdout)
        )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    missing = result.get("missing", [])
    if missing:
        raise ValueError("Configured AEDT variables were not found: {}".format(", ".join(missing)))


def main() -> int:
    args = parse_args()
    config = load_config(args.config)

    if not config.project.project_file.exists():
        raise FileNotFoundError("Baseline AEDT project not found: {}".format(config.project.project_file))
    if not INSPECTOR.exists() or not GENERIC_RUNNER.exists():
        raise FileNotFoundError("Repository automation scripts are incomplete")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case_name = args.case_name or "case_{}".format(timestamp)
    case_dir = config.project.output_root / case_name
    case_dir.mkdir(parents=True, exist_ok=False)

    project_path = case_dir / "project.aedt"
    apply_updates(
        config.project.project_file,
        project_path,
        dict(config.project.variables),
        case_dir,
    )

    command = build_runner_command(config, project_path, case_dir)
    provenance = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config_file": str(Path(args.config).resolve()),
        "baseline_project": str(config.project.project_file),
        "generated_project": str(project_path),
        "design": config.project.design,
        "setup": config.project.setup,
        "sweep": config.project.sweep,
        "ports": config.project.ports,
        "variables": dict(config.project.variables),
        "runner_command": command,
        "dry_run": args.dry_run,
    }
    (case_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )

    if args.dry_run:
        print("Prepared dry-run case: {}".format(case_dir))
        print("Command:")
        print(subprocess.list2cmdline(command))
        return 0

    completed = subprocess.run(command)
    if completed.returncode != 0:
        raise RuntimeError("HFSS runner failed with exit code {}".format(completed.returncode))

    expected = case_dir / "result.s{}p".format(config.project.ports)
    if not expected.exists():
        raise RuntimeError("HFSS completed without expected Touchstone output: {}".format(expected))

    print("Completed case: {}".format(case_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generic HFSS IronPython runner.

Compatible with the IronPython environment bundled with AEDT 2021.2. The
script keeps machine and project details outside the source code.

Usage:
  ipy64.exe scripts/run_hfss_generic.py PROJECT OUTPUT_DIR \
      --aedt-root "C:/Program Files/AnsysEM/AnsysEM21.2/Win64" \
      --design HFSSDesign1 --setup Setup1 --sweep Sweep --ports 3
"""

from __future__ import print_function

import argparse
import os
import sys
import time
import traceback
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Run one HFSS project non-graphically.")
    parser.add_argument("project_path")
    parser.add_argument("output_dir")
    parser.add_argument("--aedt-root", default=os.environ.get("HFSS_AEDT_ROOT"))
    parser.add_argument("--design", required=True)
    parser.add_argument("--setup", required=True)
    parser.add_argument("--sweep", required=True)
    parser.add_argument("--ports", type=int, required=True)
    parser.add_argument("--open-retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=int, default=8)
    return parser.parse_args()


def append_log(path, message):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a") as handle:
        handle.write("[{}] {}\n".format(stamp, message))


def open_project_with_retry(desktop, project_path, attempts, delay, log_path):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            append_log(log_path, "OpenProject attempt {}/{}".format(attempt, attempts))
            return desktop.OpenProject(project_path)
        except Exception as exc:
            last_error = exc
            append_log(log_path, "OpenProject failed: {}".format(exc))
            if attempt < attempts:
                time.sleep(delay)
    raise last_error


def main():
    args = parse_args()
    if not args.aedt_root:
        raise SystemExit("--aedt-root or HFSS_AEDT_ROOT is required")
    if args.ports <= 0:
        raise SystemExit("--ports must be positive")

    project_path = os.path.abspath(args.project_path)
    output_dir = os.path.abspath(args.output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    project_name = os.path.splitext(os.path.basename(project_path))[0]
    log_path = os.path.join(output_dir, "run.log")
    touchstone_path = os.path.join(output_dir, "result.s{}p".format(args.ports))
    profile_path = os.path.join(output_dir, "result.prof")
    convergence_path = os.path.join(output_dir, "result.conv")

    os.chdir(args.aedt_root)
    sys.path.append(args.aedt_root)
    sys.path.append(os.path.join(args.aedt_root, "PythonFiles", "DesktopPlugin"))

    import clr
    clr.AddReferenceToFileAndPath(
        os.path.join(args.aedt_root, "Ansys.Ansoft.CoreCOMScripting.dll")
    )
    import ScriptEnv

    append_log(log_path, "starting project={}".format(project_name))
    ScriptEnv.InitializeNew(NonGraphical=True)
    try:
        project = open_project_with_retry(
            oDesktop,
            project_path,
            args.open_retries,
            args.retry_delay,
            log_path,
        )
        project.SetActiveDesign(args.design)
        design = project.GetActiveDesign()
        if design is None:
            raise RuntimeError("Active design not found: {}".format(args.design))

        append_log(log_path, "analyzing design={} setup={}".format(args.design, args.setup))
        design.AnalyzeAll()

        design.ExportProfile(args.setup, "", profile_path)
        design.ExportConvergence(args.setup, "", convergence_path)

        solutions = design.GetModule("Solutions")
        solution_name = "{}:{}".format(args.setup, args.sweep)
        variations = solutions.ListVariations(solution_name)
        variation = variations[0] if len(variations) else ""
        append_log(log_path, "exporting {} ports to {}".format(args.ports, touchstone_path))
        solutions.ExportNetworkData(
            variation,
            [solution_name],
            args.ports,
            touchstone_path,
            ["All"],
            True,
            50,
            "S",
            -1,
            0,
            15,
            True,
            False,
            False,
        )
        project.Save()
        append_log(log_path, "done")
    except Exception:
        append_log(log_path, "exception")
        append_log(log_path, traceback.format_exc())
        raise
    finally:
        try:
            ScriptEnv.Shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()

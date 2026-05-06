import argparse
import ast
import json
import re
from pathlib import Path


VAR_RE = re.compile(r"VariableProp\('([^']+)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)")
BLOCK_BEGIN_RE = re.compile(r"\$begin '([^']+)'")
BLOCK_END_RE = re.compile(r"\$end '([^']+)'")


def extract_named_blocks(lines, block_name):
    blocks = []
    current = []
    depth = 0
    in_block = False
    for line in lines:
        begin_match = BLOCK_BEGIN_RE.search(line)
        end_match = BLOCK_END_RE.search(line)
        if begin_match and begin_match.group(1) == block_name:
            if not in_block:
                in_block = True
                depth = 1
                current = [line.rstrip("\n")]
                continue
            depth += 1
        if in_block:
            if current is not None and (not begin_match or begin_match.group(1) != block_name):
                current.append(line.rstrip("\n"))
            if end_match and end_match.group(1) == block_name:
                depth -= 1
                if depth == 0:
                    blocks.append(current)
                    current = []
                    in_block = False
    return blocks


def parse_variables(lines):
    variables = []
    in_properties = False
    for idx, line in enumerate(lines, start=1):
        if "$begin 'Properties'" in line:
            in_properties = True
            continue
        if "$end 'Properties'" in line:
            in_properties = False
            continue
        if not in_properties:
            continue
        match = VAR_RE.search(line)
        if match:
            variables.append(
                {
                    "name": match.group(1),
                    "kind": match.group(2),
                    "flags": match.group(3),
                    "value": match.group(4),
                    "line": idx,
                }
            )
    return variables


def parse_keyvals(block_lines):
    items = []
    for raw in block_lines:
        line = raw.strip()
        if not line or line.startswith("$begin") or line.startswith("$end"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        items.append({"key": key.strip(), "value": value.strip()})
    return items


def parse_analysis(lines):
    blocks = extract_named_blocks(lines, "AnalysisSetup")
    setups = []
    for block in blocks:
        for idx, line in enumerate(block):
            if "$begin 'Setup" in line:
                name = line.strip().split("'")[1]
                chunk = []
                depth = 1
                for inner in block[idx + 1 :]:
                    if "$begin '" in inner:
                        depth += 1
                    if "$end '" in inner:
                        depth -= 1
                    chunk.append(inner)
                    if depth == 0:
                        break
                setups.append({"name": name, "properties": parse_keyvals(chunk)})
    return setups


def parse_optimetrics(lines):
    blocks = extract_named_blocks(lines, "Optimetrics")
    setups = []
    for block in blocks:
        current = None
        in_sweeps = False
        setup_depth = 0
        sweep_item = None
        for raw in block:
            line = raw.strip()
            if line.startswith("$begin '") and "Setup" in line and "OptimetricsSetups" not in line and current is None:
                name = line.split("'")[1]
                current = {"name": name, "properties": [], "sweeps": []}
                setups.append(current)
                setup_depth = 1
                continue
            if current is None:
                continue
            if line.startswith("$begin '"):
                setup_depth += 1
            if line == "$begin 'Sweeps'":
                in_sweeps = True
                continue
            if line == "$end 'Sweeps'":
                in_sweeps = False
                sweep_item = None
                continue
            if line.startswith("$begin 'SweepDefinition'"):
                sweep_item = {}
                current["sweeps"].append(sweep_item)
                continue
            if line.startswith("$end 'SweepDefinition'"):
                sweep_item = None
                continue
            if line.startswith("$end '"):
                setup_depth -= 1
                if setup_depth == 0:
                    current = None
                continue
            if line.startswith("$begin"):
                continue
            if in_sweeps:
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == "Variable" and sweep_item is not None:
                        sweep_item["variable"] = value.strip().strip("'")
                    elif key.strip() == "Data" and sweep_item is not None:
                        sweep_item["data"] = value.strip().strip("'")
            elif "=" in line:
                key, value = line.split("=", 1)
                current["properties"].append({"key": key.strip(), "value": value.strip()})
    return setups


def parse_variable_orders(lines):
    for idx, line in enumerate(lines, start=1):
        if "VariableOrders[" not in line:
            continue
        start = line.find("[")
        if start == -1:
            continue
        content = line[start:]
        if ":" not in content:
            continue
        try:
            names_part = content.split(":", 1)[1].rstrip("]")
            if not names_part.strip():
                continue
            names = ast.literal_eval("[" + names_part + "]")
            if names:
                return {"line": idx, "names": names}
        except Exception:
            continue
    return {"line": None, "names": []}


def inspect_file(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    return {
        "file": str(path),
        "variables": parse_variables(lines),
        "variable_order": parse_variable_orders(lines),
        "analysis_setups": parse_analysis(lines),
        "optimetrics_setups": parse_optimetrics(lines),
    }


def update_variables(path, updates, output_path=None):
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines(keepends=True)
    updated_names = set()
    result = []

    for line in lines:
        match = VAR_RE.search(line)
        if not match:
            result.append(line)
            continue
        name, kind, flags, value = match.groups()
        if name not in updates:
            result.append(line)
            continue
        new_value = updates[name]
        replacement = f"VariableProp('{name}', '{kind}', '{flags}', '{new_value}')"
        updated_line = line[: match.start()] + replacement + line[match.end() :]
        result.append(updated_line)
        updated_names.add(name)

    missing = sorted(set(updates) - updated_names)
    destination = output_path or path.with_name(f"{path.stem}.updated{path.suffix}")
    destination.write_text("".join(result), encoding="utf-8")
    return {
        "source": str(path),
        "output": str(destination),
        "updated": sorted(updated_names),
        "missing": missing,
    }


def main():
    parser = argparse.ArgumentParser(description="Inspect AEDT project text structure.")
    parser.add_argument("paths", nargs="*", help="AEDT files to inspect. Defaults to all *.aedt in cwd.")
    parser.add_argument("--out", help="Write JSON output to file.")
    parser.add_argument("--set", help="JSON file containing variable updates.")
    parser.add_argument("--write-to", help="Path for updated AEDT output. Only valid with --set and one input file.")
    args = parser.parse_args()

    paths = [Path(p) for p in args.paths] if args.paths else sorted(Path.cwd().glob("*.aedt"))
    if args.set:
        if len(paths) != 1:
            raise SystemExit("--set requires exactly one AEDT input file.")
        updates = json.loads(Path(args.set).read_text(encoding="utf-8"))
        data = update_variables(paths[0], updates, Path(args.write_to) if args.write_to else None)
    else:
        data = [inspect_file(path) for path in paths]

    rendered = json.dumps(data, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()

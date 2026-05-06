# HFSS Parameter Experiment Workflow (Reusable)

This note documents a repeatable workflow for batch parameter experiments on Ansys HFSS projects (`.aedt`) with:
- derived-copy generation (no edits to the original project),
- automatic enforcement of geometric alignment constraints (via expressions),
- non-graphical solves via HFSS IronPython,
- Touchstone export (`.s3p`) + auto-plots for quick inspection,
- lightweight numeric metrics extraction for ranking candidates.

All paths/commands below are based on this workspace root: `D:\Desktop\HFSS_real`.

## 1) Prereqs / Environment

- HFSS installed (this workspace used AnsysEM 2021.2).
- IronPython runner (example):
  - `E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe`
- Repository utilities:
  - `tools/aedt_inspect.py` (parses variables and writes derived `.aedt` copies with variable updates)
  - `12GHzdiplexer/scripts/run_hfss_case.py` (opens a project, `AnalyzeAll()`, exports `.s3p/.prof/.conv`)

## 2) Core Idea: Always Work on Derived Copies

Never tune the original `.aedt` directly. For each experiment case:
1. Create a case folder under a model-specific `derived/` directory.
2. Write a `updates.json` that contains only variable updates (strings with units or expressions).
3. Materialize a new `.aedt` by applying updates to the base project using `tools/aedt_inspect.py`.
4. Run HFSS on that derived `.aedt` and export `.s3p`.
5. Plot and/or compute metrics.

This ensures:
- reproducibility (each case is a folder),
- no cross-case contamination,
- easy re-run and diff.

## 3) How `.aedt` Variables Work (What We Edit)

`.aedt` is text. In the `$begin 'Properties'` block, variables are stored as:
`VariableProp('VarName', 'UD', '', 'ValueOrExpression')`

Example variables from `12GHzdiplexer2\12GHzdiplexer.aedt`:
- `w_C1_y` (mm)
- `L4_g312g` (mm)
- `L2_g312g` (mm)
- `index1` (m in this project)
- `compensation_y` (mm)
- `compensation_y_2` (mm)

We update variables by replacing the `'ValueOrExpression'` string only.

## 4) Geometric Alignment Constraints (Face-to-Face)

### 4.1 What You Tell the Agent

Give constraints as: “FaceA must align to FaceB in Y”.
Example used in this work:
- `Face182` must align to `Face782` in Y.
- `Face634` must align to `Face730` in Y.

### 4.2 How We Implement Constraints Robustly

Do NOT hardcode `compensation_y` numeric values per case. Instead, encode constraints as expressions so geometry follows any other parameter updates.

For `12GHzdiplexer2`, the constraints were implemented as expressions:

- `compensation_y` (HPF tail alignment):
  - Stored as:
    - `compensation_y = L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g`
  - Meaning: the HPF output tail end (`Face182`) aligns with the substrate end (`Face782`) at `Y = l_sub12g`.

- `compensation_y_2` (LPF tail alignment):
  - Stored as:
    - `compensation_y_2 = l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + l_L112g + l_line412g - l_sub_LPF12g`
  - Meaning: the LPF output tail end (`Face634`) aligns with the LPF substrate end (`Face730`) at `Y = -l_sub_LPF12g` (project-specific coordinate convention).

These expressions were injected into every case’s `updates.json` so alignment stays valid during sweeps.

## 5) Batch Case Generation

### 5.1 Variable Inspection

Inspect variables and setups:
```powershell
python .\tools\aedt_inspect.py .\12GHzdiplexer2\12GHzdiplexer.aedt --out .\12GHzdiplexer2\inspect.json
```

### 5.2 Case Materialization (Generic)

Apply one case’s `updates.json` to create a derived project:
```powershell
python .\tools\aedt_inspect.py `
  .\12GHzdiplexer2\12GHzdiplexer.aedt `
  --set .\path\to\case\updates.json `
  --write-to .\path\to\case\case_name.aedt `
  --out .\path\to\case\update_result.json
```

### 5.3 L9 Orthogonal Sweep (Fast “Wide” Search)

We used a 9-point L9 orthogonal array for 4 parameters × 3 levels each. This is a good default when:
- you have multiple parameters,
- full-factorial is too expensive,
- you want sensitivity directions quickly.

Implementation used:
- `12GHzdiplexer2/scripts/build_impedance_sweep.py`
- Output:
  - `12GHzdiplexer2/derived/impedance_sweep/manifest.json`
  - Case folders: `case_01_*` ... `case_09_*`

You can edit levels in the script:
- `LEVELS = { var: [low, mid, high], ... }`
and ensure `ALIGNMENT_UPDATES` is included in each case.

### 5.4 Local Refinement (Small Perturbations Near Best Case)

After identifying a promising case, we created a small refinement set:
- `12GHzdiplexer2/scripts/build_impedance_refine.py`
- Output:
  - `12GHzdiplexer2/derived/impedance_sweep_refine/`
  - Cases: `r01_*` ... `r08_*` (single-parameter perturbations around a center point)

This is the recommended pattern for “impedance matching + frequency shift” iteration:
1. Wide search (L9)
2. Pick a center point
3. Local 1D perturbations on the most sensitive parameters
4. Repeat with narrower steps

## 6) Running HFSS Non-Graphical and Exporting S-Parameters

HFSS runner (shared):
- `12GHzdiplexer/scripts/run_hfss_case.py`

Run one case:
```powershell
& 'E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe' `
  .\12GHzdiplexer\scripts\run_hfss_case.py `
  'D:\Desktop\HFSS_real\12GHzdiplexer2\derived\...\case.aedt' `
  'D:\Desktop\HFSS_real\12GHzdiplexer2\derived\...\sim'
```

What it produces in `sim\`:
- `*.s3p` (Touchstone 3-port network)
- `*.prof` (profile export)
- `*.conv` (convergence export)
- `run.log` (timestamped trace)

Reliability improvements added:
- `OpenProject` retry inside `12GHzdiplexer/scripts/run_hfss_case.py` (handles transient COM/open failures).

## 7) Auto-Plot After Each Run (Pop-up Per Case)

Plot script:
- `12GHzdiplexer2/scripts/plot_sparams_png.py`

Output format:
- SVG (vector), fixed Y-axis: `-50..5 dB`
- Plots: `S11`, `S21`, `S31`

Batch runner that solves then plots+opens per case:
- L9: `12GHzdiplexer2/scripts/run_impedance_sweep.py`
- refine: `12GHzdiplexer2/scripts/run_impedance_refine.py`

These scripts:
- call HFSS runner to produce `*.s3p`,
- generate `*.svg`,
- `os.startfile()` to pop open the plot automatically.

## 8) Metrics Extraction (Ranking Without Manually Eyeballing Every Plot)

We used lightweight Python one-liners to extract metrics from `.s3p`:
- Return loss: `min(S11)` and “worst” `S11` in a band
- HPF edge proxy: `S21` “first rising” 3 dB entry point
- LPF edge proxy: `S31` “right falling” 3 dB point

Notes:
- Always restrict metrics to a meaningful frequency band (example: 10–50 GHz) to avoid DC artifacts.
- For 3-port Touchstone, the magnitude order is:
  - `S11, S21, S31, S12, S22, S32, S13, S23, S33`

## 9) Troubleshooting / Failure Modes

### 9.1 `AnalyzeAll()` fails

Common causes:
- geometry becomes invalid (ports floating, zero/negative dimensions),
- airbox/ports not parameterized consistently,
- too aggressive parameter levels.

Fix pattern:
- introduce explicit alignment constraints via expressions (`compensation_y*`),
- shrink sweep bounds,
- isolate whether failure correlates with a specific parameter.

### 9.2 `OpenProject` fails (COM / transient)

Observed as:
- `OpenProject(...) - call failed`

Mitigations:
- added retry logic in `12GHzdiplexer/scripts/run_hfss_case.py`
- avoid running multiple HFSS instances simultaneously on the same project tree
- if `.aedt.lock` exists and HFSS is closed, remove stale lock manually (only if you are sure)

### 9.3 Searching in `.aedtresults` fails due to `.semaphore`

Some result cache files are locked by other processes. Prefer reading the `.aedt` text and exported `.s3p` instead of grepping inside `.aedtresults`.

## 10) How to Port This Workflow to Another Model

1. Identify the real variable names in that model (use `tools/aedt_inspect.py` output).
2. Define tuning variables (e.g., coupling widths/gaps, resonator lengths).
3. Define alignment constraints:
   - give Face IDs to align (A to B in Y/X).
   - derive the controlling compensation variable(s).
   - implement as expressions (preferred) and inject into every case.
4. Create a “wide” sweep:
   - choose 3 levels per variable (safe bounds first).
   - start with L9 (9 runs) for 4 variables; expand only if necessary.
5. Run non-graphical solves:
   - export `*.s3p` per case.
6. Plot + open per case for quick human scan.
7. Compute metrics and pick a center point.
8. Run refine (single-parameter perturbations) until convergence.

## Files Created/Used in This Workspace

- `tools/aedt_inspect.py`
- `12GHzdiplexer/scripts/run_hfss_case.py`
- `12GHzdiplexer2/scripts/plot_sparams_png.py`
- `12GHzdiplexer2/scripts/build_impedance_sweep.py`
- `12GHzdiplexer2/scripts/run_impedance_sweep.py`
- `12GHzdiplexer2/scripts/build_impedance_refine.py`
- `12GHzdiplexer2/scripts/run_impedance_refine.py`


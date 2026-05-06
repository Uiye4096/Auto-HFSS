# run_and_plot.ps1
# Usage: .\tools\run_and_plot.ps1 <aedt_path> <output_dir>
# Runs HFSS simulation then plots the resulting .s3p as SVG and opens it.
param(
    [Parameter(Mandatory)][string]$AedtPath,
    [Parameter(Mandatory)][string]$OutputDir
)

$IPY   = "E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe"
$SCRIPT = "$PSScriptRoot\..\12GHzdiplexer\scripts\run_hfss_case.py"
$PLOT   = "$PSScriptRoot\plot_s3p.py"

Write-Host "==> Running HFSS: $AedtPath"
& $IPY $SCRIPT $AedtPath $OutputDir
if ($LASTEXITCODE -ne 0) { Write-Error "HFSS run FAILED (exit $LASTEXITCODE)"; exit 1 }

$projectName = [System.IO.Path]::GetFileNameWithoutExtension($AedtPath)
$s3p = Join-Path $OutputDir "$projectName.s3p"

Write-Host "==> Plotting: $s3p"
python $PLOT $s3p --open

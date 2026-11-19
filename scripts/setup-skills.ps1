# Recria as junctions .claude\skills\<skill> -> vendor\cut-as-code\skills\<skill>
# Uso (não altera a política de execução do sistema):
#   powershell -ExecutionPolicy Bypass -File scripts\setup-skills.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vendorSkills = Join-Path $root 'vendor\cut-as-code\skills'
if (-not (Test-Path $vendorSkills)) {
    throw "Submódulo em falta. Corre primeiro: git submodule update --init"
}
$skills = 'cut-as-code','video-understand','video-cut','video-to-shorts',
          'video-add-captions','video-add-content-cards','video-edit-compare'
$dest = Join-Path $root '.claude\skills'
New-Item -ItemType Directory -Force $dest | Out-Null
foreach ($s in $skills) {
    $link = Join-Path $dest $s
    if (Test-Path $link) { Write-Host "ok      $s"; continue }
    cmd /c mklink /J "$link" "$(Join-Path $vendorSkills $s)" | Out-Null
    Write-Host "criado  $s"
}

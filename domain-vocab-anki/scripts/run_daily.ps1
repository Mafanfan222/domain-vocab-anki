param(
    [Parameter(Mandatory=$true)][string]$ConfigPath,
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
$config = (Resolve-Path -LiteralPath $ConfigPath).Path
$project = (Resolve-Path -LiteralPath $ProjectRoot).Path
$state = Join-Path $project 'state/learning.sqlite3'
$lessons = Join-Path $project 'lessons'
$logDir = Join-Path $project 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format 'yyyy-MM-dd'
$log = Join-Path $logDir "$stamp.log"
$venvPython = Join-Path $project '.venv/Scripts/python.exe'
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { 'python' }
& $python -m domain_vocab_anki.cli run --config $config --state $state --output $lessons *>&1 | Out-File -FilePath $log -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "Lesson run failed; see $log" }

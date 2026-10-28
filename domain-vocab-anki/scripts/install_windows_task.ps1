param(
    [Parameter(Mandatory=$true)][string]$ConfigPath,
    [string]$TaskName = 'DomainVocabAnkiDaily',
    [string]$At = '09:00'
)

$ErrorActionPreference = 'Stop'
$config = (Resolve-Path -LiteralPath $ConfigPath).Path
$runner = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'run_daily.ps1')).Path
$quotedRunner = '"' + $runner + '"'
$quotedConfig = '"' + $config + '"'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File $quotedRunner -ConfigPath $quotedConfig"
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Daily domain English lesson and local Anki sync' -Force | Out-Null
Write-Output "Installed $TaskName at $At every day (including weekends)."

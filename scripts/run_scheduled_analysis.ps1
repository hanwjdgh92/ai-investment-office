# Windows 작업 스케줄러가 하루 3회(09:00/16:00/23:30) 호출하는 전체분석 스크립트.
# claude -p "/scheduled-analysis" 를 프로젝트 폴더에서 헤드리스로 실행하고 결과를 logs/에 UTF-8로 남긴다.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

$LogsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$LogFile = Join-Path $LogsDir "scheduled_$Timestamp.log"

Set-Location $ProjectRoot

$ClaudeExe = "C:\Users\user\.local\bin\claude.exe"

# ponytail: $ErrorActionPreference=Stop + "2>&1 |" turns every native stderr line (even
# benign warnings, e.g. workspace-trust notices) into a terminating NativeCommandError in
# PowerShell 5.1, killing the run before the log is written. Relax to Continue only around
# this call so stderr still lands in the UTF-8 log instead of aborting the script.
$PrevErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $ClaudeExe -p "/scheduled-analysis" --permission-mode acceptEdits --max-budget-usd 3 --output-format text 2>&1 | Out-File -FilePath $LogFile -Encoding utf8
$ErrorActionPreference = $PrevErrorActionPreference

Write-Output "완료: $LogFile"

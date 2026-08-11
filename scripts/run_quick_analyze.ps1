# 라이브 서버(scripts/serve_office.py)가 검색창 즉시분석 요청을 받았을 때 백그라운드로 실행하는 스크립트.
# claude -p "/quick-analyze <Type> <Symbol>" 를 헤드리스로 실행하고 결과를 -LogFile 에 UTF-8로 남긴다.
# run_scheduled_analysis.ps1과 같은 이유로 이 파일 자체를 UTF-8 BOM으로 저장한다(한글 깨짐 방지).

param(
    [Parameter(Mandatory = $true)][string]$Type,
    [Parameter(Mandatory = $true)][string]$Symbol,
    [Parameter(Mandatory = $true)][string]$LogFile,
    [Parameter(Mandatory = $true)][string]$MaxBudgetUsd
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Set-Location $ProjectRoot

$ClaudeExe = "C:\Users\user\.local\bin\claude.exe"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PrevErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $ClaudeExe -p "/quick-analyze $Type $Symbol" --permission-mode acceptEdits --max-budget-usd $MaxBudgetUsd --output-format text 2>&1 | Out-File -FilePath $LogFile -Encoding utf8
$ErrorActionPreference = $PrevErrorActionPreference

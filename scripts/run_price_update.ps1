# Windows 작업 스케줄러가 매시간 호출하는 경량 갱신 스크립트.
# LLM을 호출하지 않고 가격/지표 데이터만 새로 받아 office 스냅샷을 갱신한다. 비용 없음.

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Set-Location $ProjectRoot

$hasError = $false
$pyScripts = @("fetch_crypto.py", "fetch_stocks_kr.py", "fetch_stocks_us.py", "fetch_macro.py", "generate_office.py")
foreach ($script in $pyScripts) {
    try {
        python "scripts\$script"
        if ($LASTEXITCODE -ne 0) {
            Write-Output "실패: $script (종료 코드 $LASTEXITCODE)"
            $hasError = $true
        }
    } catch {
        Write-Output "실패: $script - $_"
        $hasError = $true
    }
}

if ($hasError) {
    exit 1
}

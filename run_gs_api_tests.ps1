# ============================================================
# 高升AI接口自动化 - Windows PowerShell 一键运行脚本
# 用法:
#   ./run_gs_api_tests.ps1              # 跑冒烟用例并生成 Allure HTML
#   ./run_gs_api_tests.ps1 -All         # 跑全量用例(含语音/ragas)
#   ./run_gs_api_tests.ps1 -Markers "session and chat"  # 自定义 markers
# ============================================================

param(
    [string]$Markers = "smoke",
    [switch]$All,
    [switch]$SkipReport,
    [switch]$OpenReport
)

$ErrorActionPreference = "Stop"

# ---------- 路径与环境 ----------
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    $PyExe = "python"
} else {
    $PyExe = ".venv\Scripts\python.exe"
}

if ($All) { $Markers = "" }

$AllureResults = "gs_api\report\output\allure_results"
$AllureHtml    = "gs_api\report\output\allure_html"

New-Item -ItemType Directory -Force -Path $AllureResults | Out-Null

# ---------- 执行 pytest ----------
Write-Host "`n[1/2] 运行 pytest  markers=$Markers" -ForegroundColor Cyan
$PytestArgs = @(
    "-m", "`"$Markers`"",
    "gs_api/script",
    "-v",
    "--strict-markers",
    "--tb=short",
    "--alluredir=$AllureResults",
    "--clean-alluredir"
)
& $PyExe -m pytest @PytestArgs
$PytestExit = $LASTEXITCODE

# ---------- 生成 Allure 报告 ----------
if (-not $SkipReport) {
    Write-Host "`n[2/2] 生成 Allure HTML 报告..." -ForegroundColor Cyan
    if (Test-Path $AllureHtml) { Remove-Item -Recurse -Force $AllureHtml }
    try {
        allure generate $AllureResults -o $AllureHtml --clean
        if ($OpenReport) {
            Start-Process allure -ArgumentList "open", $AllureHtml
        }
        Write-Host "`nAllure 报告目录: $(Resolve-Path $AllureHtml)" -ForegroundColor Green
    } catch {
        Write-Warning "未安装 allure 命令行，跳过 HTML 报告生成：https://allurereport.org/docs/getting-started-installation/"
    }
}

Write-Host "`n[完成] pytest退出码=$PytestExit" -ForegroundColor $(if ($PytestExit -eq 0) {"Green"} else {"Red"})
exit $PytestExit

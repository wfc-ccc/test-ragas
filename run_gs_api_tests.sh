#!/usr/bin/env bash
# ============================================================
# 高升AI接口自动化 - macOS / Linux 一键运行脚本
# 用法:
#   bash run_gs_api_tests.sh               # 冒烟用例 + Allure HTML
#   bash run_gs_api_tests.sh all           # 全量用例
#   MARKERS="session and chat" bash run_gs_api_tests.sh
# ============================================================
set -euo pipefail

cd "$(dirname "$0")"

MARKERS="${MARKERS:-smoke}"
ALLURE_RESULTS="gs_api/report/output/allure_results"
ALLURE_HTML="gs_api/report/output/allure_html"

if [[ "${1:-}" == "all" ]]; then
    MARKERS=""
fi

mkdir -p "$ALLURE_RESULTS"

echo "[1/2] 运行 pytest  markers=$MARKERS"
if [ -x ".venv/bin/python" ]; then
    PYEXE=".venv/bin/python"
else
    PYEXE="python3"
fi

set +e
$PYEXE -m pytest gs_api/script \
    ${MARKERS:+-m "$MARKERS"} \
    -v --strict-markers --tb=short \
    --alluredir="$ALLURE_RESULTS" --clean-alluredir
PYTEST_EXIT=$?
set -e

echo "[2/2] 生成 Allure HTML 报告..."
rm -rf "$ALLURE_HTML"
if command -v allure >/dev/null 2>&1; then
    allure generate "$ALLURE_RESULTS" -o "$ALLURE_HTML" --clean
    echo "Allure 报告: $ALLURE_HTML/index.html"
else
    echo "⚠️  未找到 allure 命令，跳过 HTML 生成"
fi

echo ""
echo "[完成] pytest 退出码=$PYTEST_EXIT"
exit $PYTEST_EXIT

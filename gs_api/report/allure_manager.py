"""
Allure 报告管理。

负责：
- 生成 Allure 环境文件（environment.properties）
- 生成分类文件（categories.json）
- 清理历史结果目录
- 生成 HTML 报告的命令封装
- 将 Ragas 评估结果以附件形式挂载到 Allure
"""

import json
import shutil
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional

import allure
import pandas as pd

from ..base import config, REPORT_DIR, get_logger

log = get_logger(__name__)

ALLURE_RESULTS = Path(config.get("allure.report_dir", str(REPORT_DIR / "allure_results")))
ALLURE_HTML = REPORT_DIR / "allure_html"

ALLURE_RESULTS.mkdir(parents=True, exist_ok=True)


class AllureManager:
    """Allure 报告管理器。"""

    @staticmethod
    def clean_results() -> None:
        """清空 allure-results 目录（保留目录本身）。"""
        if ALLURE_RESULTS.exists() and config.get("allure.clean", True):
            for child in ALLURE_RESULTS.iterdir():
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
            log.info("已清空 Allure 结果目录: %s", ALLURE_RESULTS)

    @staticmethod
    def write_environment() -> None:
        """写入 environment.properties，展示框架运行环境。"""
        env_file = ALLURE_RESULTS / "environment.properties"
        lines = [
            f"Project=高升AI接口自动化测试",
            f"BaseURL={config.base_url}",
            f"Python={platform.python_version()}",
            f"Platform={platform.platform()}",
            f"OS={platform.system()} {platform.release()}",
            f"RunTime={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"RagasEnabled={config.get('ragas.enabled', True)}",
            f"SeleniumBrowser={config.get('selenium.browser', 'chrome')}",
        ]
        env_file.write_text("\n".join(lines), encoding="utf-8")
        log.info("Allure environment 信息已写入")

    @staticmethod
    def write_categories() -> None:
        """写入 categories.json 用于按模块/缺陷类型归类用例。"""
        cats = [
            {
                "name": "会话接口缺陷",
                "matchedStatuses": ["broken", "failed"],
                "messageRegex": r".*session.*",
            },
            {
                "name": "聊天接口缺陷",
                "matchedStatuses": ["broken", "failed"],
                "messageRegex": r".*chat.*",
            },
            {
                "name": "历史会话缺陷",
                "matchedStatuses": ["broken", "failed"],
                "messageRegex": r".*history.*",
            },
            {
                "name": "知识库缺陷",
                "matchedStatuses": ["broken", "failed"],
                "messageRegex": r".*embedding.*",
            },
            {
                "name": "语音接口缺陷",
                "matchedStatuses": ["broken", "failed"],
                "messageRegex": r".*audio.*",
            },
            {
                "name": "Ragas 质量不达标",
                "matchedStatuses": ["failed"],
                "messageRegex": r".*Ragas.*",
            },
        ]
        (ALLURE_RESULTS / "categories.json").write_text(
            json.dumps(cats, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def attach_ragas_table(df: pd.DataFrame, name: str = "Ragas评估明细表") -> None:
        """将 ragas 评估 DataFrame 以 CSV / HTML 形式挂载到 Allure 用例。"""
        try:
            csv_text = df.to_csv(index=False)
            allure.attach(
                csv_text,
                name=f"{name}-CSV",
                attachment_type=allure.attachment_type.CSV,
            )
            html_text = df.to_html(index=False, border=1, justify="left")
            allure.attach(
                html_text,
                name=f"{name}-HTML",
                attachment_type=allure.attachment_type.HTML,
            )
        except Exception as e:
            log.warning("挂载 ragas 表格到 Allure 失败: %s", e)

    @staticmethod
    def attach_ragas_summary(
        summary: dict,
        name: str = "Ragas评估汇总",
    ) -> None:
        """将 ragas 评估汇总（每个指标均值）挂载到 Allure。"""
        text_lines = ["=== 高升AI 回答质量评估汇总 ==="]
        for k, v in summary.items():
            if isinstance(v, float):
                text_lines.append(f"  {k:<22s}: {v:.4f}")
            else:
                text_lines.append(f"  {k:<22s}: {v}")
        allure.attach(
            "\n".join(text_lines),
            name=name,
            attachment_type=allure.attachment_type.TEXT,
        )

    @staticmethod
    def generate_html_report(
        results_dir: Optional[str | Path] = None,
        output_dir: Optional[str | Path] = None,
        open_browser: bool = False,
    ) -> int:
        """调用 allure 命令行生成 HTML 报告。

        Returns:
            allure generate 子进程退出码（0表示成功）
        """
        results = Path(results_dir) if results_dir else ALLURE_RESULTS
        output = Path(output_dir) if output_dir else ALLURE_HTML
        if output.exists():
            shutil.rmtree(output, ignore_errors=True)
        cmd = [
            "allure",
            "generate",
            str(results),
            "-o",
            str(output),
            "--clean",
        ]
        log.info("生成 Allure 报告: %s", " ".join(cmd))
        try:
            ret = subprocess.run(cmd, shell=False).returncode
        except FileNotFoundError:
            log.error(
                "未找到 allure 命令，请先安装：https://allurereport.org/docs/getting-started-installation/"
            )
            return 1
        if open_browser and ret == 0:
            subprocess.Popen(["allure", "open", str(output)])
        return ret

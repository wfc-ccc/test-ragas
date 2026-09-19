"""
配置管理模块。

统一管理高升AI接口测试框架的全局配置，
支持从 YAML 配置文件与环境变量加载参数。
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = BASE_DIR / "gs_api" / "config"
DATA_DIR = BASE_DIR / "gs_api" / "data"
REPORT_DIR = BASE_DIR / "gs_api" / "report" / "output"

DEFAULT_CONFIG = {
    "api": {
        "base_url": "http://127.0.0.1:10010",
        "timeout": 30,
        "retries": 3,
        "retry_delay": 1,
    },
    "auth": {
        "token": "",
        "token_env": "AIS_TOKEN",
    },
    "selenium": {
        "browser": "chrome",
        "headless": True,
        "implicitly_wait": 10,
        "page_load_timeout": 30,
        "window_size": "1920,1080",
        "driver_path": "",
    },
    "allure": {
        "report_dir": str(REPORT_DIR / "allure_results"),
        "clean": True,
    },
    "ragas": {
        "enabled": True,
        "metrics": ["faithfulness", "answer_relevancy", "context_recall"],
        "threshold": {
            "faithfulness": 0.6,
            "answer_relevancy": 0.6,
            "context_recall": 0.6,
        },
    },
}


class Config:
    """全局配置管理器。"""

    _instance = None
    _config: dict = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """加载配置: 默认值 -> YAML 文件 -> 环境变量 覆盖。"""
        self._config = self._deep_copy(DEFAULT_CONFIG)

        yaml_path = CONFIG_DIR / "config.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                yaml_conf = yaml.safe_load(f) or {}
            self._deep_update(self._config, yaml_conf)

        token_env = self._config["auth"]["token_env"]
        if os.getenv(token_env):
            self._config["auth"]["token"] = os.getenv(token_env)

        for key in ["DEEPSEEK_API_KEY", "EMBEDDING_API_KEY", "AIS_TOKEN"]:
            if os.getenv(key):
                pass

    @staticmethod
    def _deep_copy(d: dict) -> dict:
        import copy
        return copy.deepcopy(d)

    @staticmethod
    def _deep_update(base: dict, override: dict) -> None:
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                Config._deep_update(base[k], v)
            else:
                base[k] = v

    def get(self, key: str, default: Any = None) -> Any:
        """按点分路径获取配置，如 api.base_url。"""
        keys = key.split(".")
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        conf = self._config
        for k in keys[:-1]:
            conf = conf.setdefault(k, {})
        conf[keys[-1]] = value

    @property
    def base_url(self) -> str:
        return self.get("api.base_url")

    @property
    def timeout(self) -> int:
        return self.get("api.timeout", 30)

    @property
    def token(self) -> str:
        return self.get("auth.token", "")

    @token.setter
    def token(self, value: str) -> None:
        self.set("auth.token", value)


config = Config()

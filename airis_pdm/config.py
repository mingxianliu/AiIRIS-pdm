"""設定檔載入."""

import json
from pathlib import Path


def load_config(config_path: str = "figma-sync.config.json") -> dict:
    """載入 JSON 設定檔，不存在則回傳空 dict."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

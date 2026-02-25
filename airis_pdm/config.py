"""設定檔載入與基本驗證."""

import json
from pathlib import Path
from typing import Any

# 已知有效的頂層欄位
_KNOWN_TOP_KEYS = {"figma", "source", "viewport", "naming", "export"}

# 各區塊已知欄位（用於拼字提示）
_KNOWN_SECTION_KEYS = {
    "figma": {"personalAccessToken", "fileKey"},
    "source": {"framework", "styleStrategy", "entryUrl", "srcRoot"},
    "viewport": {"width", "height", "deviceName"},
    "naming": {"separator", "ignoreClasses"},
    "export": {"snapshotDir", "cjkFontFamily"},
}

_VALID_FRAMEWORKS = {"html", "vue", "react", "svelte", "next", "nuxt"}
_VALID_STRATEGIES = {"tailwind", "css-modules", "scss", "inline"}


def _warn(msg: str) -> None:
    print(f"   ⚠️  [config] {msg}")


def validate_config(cfg: dict) -> None:
    """對 config 做基本欄位驗證，印出警告但不拋例外。"""
    if not cfg:
        return

    # 頂層未知欄位
    for key in cfg:
        if key not in _KNOWN_TOP_KEYS:
            known = ", ".join(sorted(_KNOWN_TOP_KEYS))
            _warn(f"未知頂層欄位 '{key}'（已知欄位：{known}）")

    # 各區塊欄位
    for section, known_keys in _KNOWN_SECTION_KEYS.items():
        section_cfg = cfg.get(section, {})
        if not isinstance(section_cfg, dict):
            continue
        for key in section_cfg:
            if key not in known_keys:
                known = ", ".join(sorted(known_keys))
                _warn(f"[{section}] 未知欄位 '{key}'（已知欄位：{known}）")

    # source.framework 值驗證
    framework = cfg.get("source", {}).get("framework")
    if framework and framework not in _VALID_FRAMEWORKS:
        valid = ", ".join(sorted(_VALID_FRAMEWORKS))
        _warn(f"source.framework '{framework}' 不在已知值中（{valid}）")

    # source.styleStrategy 值驗證
    strategy = cfg.get("source", {}).get("styleStrategy")
    if strategy and strategy not in _VALID_STRATEGIES:
        valid = ", ".join(sorted(_VALID_STRATEGIES))
        _warn(f"source.styleStrategy '{strategy}' 不在已知值中（{valid}）")

    # viewport 值類型
    for dim in ("width", "height"):
        val = cfg.get("viewport", {}).get(dim)
        if val is not None and not isinstance(val, (int, float)):
            _warn(f"viewport.{dim} 應為數字，目前是 {type(val).__name__}")

    # srcRoot 存在性提示（不強制，可能是 CI 環境）
    src_root = cfg.get("source", {}).get("srcRoot")
    if src_root and not Path(src_root).exists():
        _warn(f"source.srcRoot '{src_root}' 目錄不存在（pull --apply 時需要）")


def load_config(config_path: str = "figma-sync.config.json") -> dict:
    """載入 JSON 設定檔，不存在則回傳空 dict；存在則做基本驗證。"""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        cfg: Any = json.load(f)
    if not isinstance(cfg, dict):
        print(f"   ⚠️  [config] '{config_path}' 格式錯誤，應為 JSON 物件，回傳空設定。")
        return {}
    validate_config(cfg)
    return cfg

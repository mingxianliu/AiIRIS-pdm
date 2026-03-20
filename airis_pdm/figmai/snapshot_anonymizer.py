"""
真實專案快照匿名化工具：保留結構，遮罩可識別字串。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def anonymize_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """將快照中的文字欄位做穩定匿名化（同值同代號）。"""
    data = deepcopy(payload)
    mapping: Dict[str, str] = {}
    counter = {"n": 0}

    def mask(s: str) -> str:
        if s in mapping:
            return mapping[s]
        counter["n"] += 1
        token = f"TXT_{counter['n']:04d}"
        mapping[s] = token
        return token

    def walk(v: Any, key: str | None = None) -> Any:
        if isinstance(v, dict):
            out = {}
            for k, val in v.items():
                out[k] = walk(val, k)
            return out
        if isinstance(v, list):
            return [walk(x, key) for x in v]
        if isinstance(v, str):
            # 保留路由、色碼、型別等結構值，不做遮罩
            if key in {"id", "type", "routePath", "slug", "pattern"}:
                return v
            if v.startswith("#") or v.startswith("rgb") or v.startswith("rgba"):
                return v
            if v.startswith("[Page]"):
                return "[Page] " + mask(v[len("[Page] "):] if v.startswith("[Page] ") else v)
            return mask(v)
        return v

    anonymized = walk(data)
    if isinstance(anonymized, dict):
        anonymized["_anonymizeMapSize"] = len(mapping)
    return anonymized

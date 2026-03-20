from __future__ import annotations

from typing import Any, Dict, Iterable, List


def walk_ui_ir(node: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    yield node
    for child in node.get("children") or []:
        yield from walk_ui_ir(child)


def parse_variant_kv(name: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in (name or "").split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def collect_texts(node: Dict[str, Any]) -> List[str]:
    texts: List[str] = []
    for n in walk_ui_ir(node):
        if str(n.get("sourceType", "")).upper() == "TEXT":
            txt = (n.get("text") or {}).get("characters") or n.get("name")
            if isinstance(txt, str) and txt.strip():
                texts.append(txt.strip())
    return texts


def to_int(val: Any, default: int = 0) -> int:
    try:
        if val is None:
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default

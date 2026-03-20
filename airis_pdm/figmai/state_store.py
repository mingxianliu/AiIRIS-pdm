"""
FigmAI chain 狀態映射儲存：pencil id ↔ figma node id。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChainState:
    nodes: Dict[str, str] = field(default_factory=dict)
    orphans: Dict[str, str] = field(default_factory=dict)
    last_sync: str = ""


class StateStore:
    """對齊舊 TS StateStore：讀寫 state.json。"""

    def __init__(self, output_dir: str, filename: str = "state.json"):
        self.file_path = Path(output_dir) / filename
        self.state = ChainState()

    def load(self) -> None:
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            self.state = ChainState(
                nodes=dict(data.get("nodes") or {}),
                orphans=dict(data.get("orphans") or {}),
                last_sync=str(data.get("lastSync") or data.get("last_sync") or ""),
            )
        except Exception:  # noqa: BLE001
            self.state = ChainState()

    def save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(
                {
                    "nodes": self.state.nodes,
                    "orphans": self.state.orphans,
                    "lastSync": self.state.last_sync,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def get_figma_id(self, pencil_id: str) -> Optional[str]:
        return self.state.nodes.get(pencil_id)

    def set_mapping(self, pencil_id: str, figma_id: str) -> None:
        self.state.nodes[pencil_id] = figma_id
        self.state.orphans.pop(pencil_id, None)
        self.state.last_sync = _now_iso()

    def remove_mapping(self, pencil_id: str) -> Optional[str]:
        figma_id = self.state.nodes.pop(pencil_id, None)
        self.state.last_sync = _now_iso()
        return figma_id

    def mark_orphan(self, pencil_id: str, figma_id: str) -> None:
        self.state.nodes.pop(pencil_id, None)
        self.state.orphans[pencil_id] = figma_id
        self.state.last_sync = _now_iso()

    def clear(self) -> None:
        self.state.nodes = {}
        self.state.orphans = {}
        self.state.last_sync = _now_iso()

"""
AiIRIS-pdm — Code ↔ Figma 雙向同步（Python 管線）

彙整 figma-code-sync 的 IR / 命名引擎與 ErSlice 的設計資產概念。
"""

__version__ = "0.2.0"

from .naming_engine import (
    NamingConfig,
    NamingEngine,
    VueComponentDetector,
    ReactComponentDetector,
    preview_naming_tree,
)
from .dom_extractor import extract_dom_tree, extract_dom_tree_sync, ExtractionConfig
from .ir_builder import IRBuilderV2, build_ir_from_extraction, save_ir

# 對外 API 使用 IRBuilder（與 IRBuilderV2 為同一實作）
IRBuilder = IRBuilderV2
from .figma_reader import FigmaAPIClient, FigmaToIR, IRDiffer
from .code_patcher import CodePatcher
from .config import load_config
from . import design_assets

__all__ = [
    "__version__",
    "NamingConfig",
    "NamingEngine",
    "VueComponentDetector",
    "ReactComponentDetector",
    "preview_naming_tree",
    "extract_dom_tree",
    "extract_dom_tree_sync",
    "ExtractionConfig",
    "IRBuilder",
    "IRBuilderV2",
    "build_ir_from_extraction",
    "save_ir",
    "FigmaAPIClient",
    "FigmaToIR",
    "IRDiffer",
    "CodePatcher",
    "load_config",
    "design_assets",
]

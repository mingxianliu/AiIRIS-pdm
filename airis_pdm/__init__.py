"""
AiIRIS-pdm — Code ↔ Figma 雙向同步（Python 管線）

彙整 figma-code-sync 的 IR / 命名引擎與 ErSlice 的設計資產概念。
"""

__version__ = "0.4.0"

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
from .code_patcher import CodePatcher, find_files_by_selector, url_to_local_path
from .config import load_config, validate_config
from . import design_assets
from .generator import generate_project

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
    "find_files_by_selector",
    "url_to_local_path",
    "load_config",
    "validate_config",
    "design_assets",
    "generate_project",
]

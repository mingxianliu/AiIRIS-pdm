"""AiIRIS-pdm — Spec → Pencil AI → Fine-tune → React/Vue Code

工作流：
    1. 從規格（Spec）→ 透過 Pencil AI 產生 UI 設計
    2. 人工在 Pencil AI 中微調
    3. 從 .pen → IR v2.0 → 產生 React/Vue/HTML/Flutter 程式碼
"""

__version__ = "0.5.0"

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

# Pencil AI 整合（新工作流主力）
from .pencil_reader import PencilToIR
from .pencil_mcp_tools import PencilMcpTools
from .generator import generate_from_ir

from .code_patcher import CodePatcher, find_files_by_selector, url_to_local_path
from .config import load_config, validate_config
from . import design_assets
from .token_export import extract_tokens_from_ir, export_tokens
from .theme_manager import ThemeManager
from .visual_compliance import run_visual_compliance, run_visual_compliance_sync, VisualComplianceResult

# 向下相容（deprecated — 將在 0.6.0 移除）
try:
    from .figma_reader import FigmaAPIClient, FigmaToIR, IRDiffer
    from .figma_mcp_tools import FigmaMcpTools
    from .generator import generate_project
except ImportError:
    FigmaAPIClient = None  # type: ignore[assignment,misc]
    FigmaToIR = None  # type: ignore[assignment,misc]
    IRDiffer = None  # type: ignore[assignment,misc]
    FigmaMcpTools = None  # type: ignore[assignment,misc]
    generate_project = None  # type: ignore[assignment]

__all__ = [
    "__version__",
    # Naming / DOM / IR
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
    # Pencil AI（新工作流）
    "PencilToIR",
    "PencilMcpTools",
    "generate_from_ir",
    # Code patcher / Config
    "CodePatcher",
    "find_files_by_selector",
    "url_to_local_path",
    "load_config",
    "validate_config",
    "design_assets",
    "extract_tokens_from_ir",
    "export_tokens",
    "ThemeManager",
    "run_visual_compliance",
    "run_visual_compliance_sync",
    "VisualComplianceResult",
    # Deprecated (Figma)
    "FigmaAPIClient",
    "FigmaToIR",
    "IRDiffer",
    "FigmaMcpTools",
    "generate_project",
]

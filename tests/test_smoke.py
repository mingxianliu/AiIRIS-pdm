"""
Smoke tests：驗證套件可匯入、版本與公開 API 存在。
"""
import pytest


def test_import_package():
    """套件可正常匯入"""
    import airis_pdm
    assert airis_pdm.__version__ == "0.2.0"


def test_public_api():
    """公開 API 可從 airis_pdm 取得"""
    from airis_pdm import (
        __version__,
        extract_dom_tree,
        extract_dom_tree_sync,
        ExtractionConfig,
        build_ir_from_extraction,
        save_ir,
        IRBuilder,
        IRBuilderV2,
        preview_naming_tree,
        load_config,
    )
    assert __version__ == "0.2.0"
    assert IRBuilder is IRBuilderV2
    assert callable(extract_dom_tree)
    assert callable(build_ir_from_extraction)
    assert callable(save_ir)
    assert callable(load_config)


def test_ir_builder_build_ir_from_extraction_signature():
    """build_ir_from_extraction 接受 (extraction_result, config)"""
    from airis_pdm import build_ir_from_extraction

    # 最小合法 DOM 樹 + 基本 config
    minimal_tree = {
        "tag": "div",
        "attrs": {},
        "layout": {"x": 0, "y": 0, "width": 100, "height": 100},
        "children": [],
    }
    extraction = {"tree": minimal_tree, "viewport": {"width": 1440, "height": 900}}
    config = {"source": {"framework": "html"}, "naming": {}}
    result = build_ir_from_extraction(extraction, config)
    assert "tree" in result
    assert result.get("version") == "2.0.0"
    assert result["tree"] is not None

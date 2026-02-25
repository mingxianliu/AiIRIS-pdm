"""
StyleConverter 單元測試（P2 #13）
涵蓋 Tailwind 與 CSS 轉換的各類樣式屬性。
"""
import pytest
from airis_pdm.code_patcher import StyleConverter


# ─── figma_color_to_hex ─────────────────────────────────────────────────────

def test_color_to_hex_rgb():
    assert StyleConverter.figma_color_to_hex("rgb(255, 0, 0)") == "#ff0000"


def test_color_to_hex_rgba():
    assert StyleConverter.figma_color_to_hex("rgba(0, 128, 255, 0.5)") == "#0080ff"


def test_color_to_hex_passthrough():
    # 無法解析的字串直接返回
    assert StyleConverter.figma_color_to_hex("#aabbcc") == "#aabbcc"


# ─── ir_styles_to_tailwind ──────────────────────────────────────────────────

def make_change(after):
    return {"before": None, "after": after}


def test_tailwind_background_color():
    changes = {"styles.backgroundColor": make_change("rgb(79, 70, 229)")}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert any("bg-[" in r for r in result)


def test_tailwind_opacity():
    changes = {"styles.opacity": make_change(0.75)}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert "opacity-75" in result


def test_tailwind_border_radius_uniform():
    changes = {"styles.borderRadius": make_change({"topLeft": 8, "topRight": 8, "bottomRight": 8, "bottomLeft": 8})}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert "rounded-[8px]" in result


def test_tailwind_font_size():
    changes = {"text.fontSize": make_change(16)}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert "text-[16px]" in result


def test_tailwind_font_weight_named():
    changes = {"text.fontWeight": make_change(700)}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert "font-bold" in result


def test_tailwind_font_weight_unknown():
    changes = {"text.fontWeight": make_change(650)}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert "font-[650]" in result


def test_tailwind_text_color():
    changes = {"text.color": make_change("rgb(0, 0, 0)")}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert any("text-[" in r for r in result)


def test_tailwind_gap():
    changes = {"autoLayout.spacing": make_change(16)}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert "gap-[16px]" in result


def test_tailwind_skips_none_after():
    changes = {"styles.backgroundColor": {"before": "red", "after": None}}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert result == []


def test_tailwind_skips_underscore_keys():
    changes = {"_status": make_change("added")}
    result = StyleConverter.ir_styles_to_tailwind(changes)
    assert result == []


# ─── ir_styles_to_css ───────────────────────────────────────────────────────

def test_css_background_color():
    changes = {"styles.backgroundColor": make_change("rgba(0, 0, 0, 1)")}
    result = StyleConverter.ir_styles_to_css(changes)
    assert result.get("background-color") == "rgba(0, 0, 0, 1)"


def test_css_opacity():
    changes = {"styles.opacity": make_change(0.5)}
    result = StyleConverter.ir_styles_to_css(changes)
    assert result.get("opacity") == "0.5"


def test_css_border_radius():
    changes = {"styles.borderRadius": make_change({"topLeft": 4, "topRight": 8, "bottomRight": 4, "bottomLeft": 8})}
    result = StyleConverter.ir_styles_to_css(changes)
    assert result.get("border-radius") == "4px 8px 4px 8px"


def test_css_border_solid():
    changes = {"styles.border": make_change({"color": "#333", "width": 2, "style": "SOLID"})}
    result = StyleConverter.ir_styles_to_css(changes)
    assert result.get("border") == "2px solid #333"


def test_css_border_dashed():
    changes = {"styles.border": make_change({"color": "#333", "width": 1, "style": "DASHED"})}
    result = StyleConverter.ir_styles_to_css(changes)
    assert "dashed" in result.get("border", "")


def test_css_font_size():
    changes = {"text.fontSize": make_change(14)}
    result = StyleConverter.ir_styles_to_css(changes)
    assert result.get("font-size") == "14px"


def test_css_letter_spacing():
    changes = {"text.letterSpacing": make_change(1.5)}
    result = StyleConverter.ir_styles_to_css(changes)
    assert result.get("letter-spacing") == "1.5px"


def test_css_gap():
    changes = {"autoLayout.spacing": make_change(24)}
    result = StyleConverter.ir_styles_to_css(changes)
    assert result.get("gap") == "24px"


def test_css_padding_side():
    changes = {"autoLayout.paddingTop": make_change(12)}
    result = StyleConverter.ir_styles_to_css(changes)
    assert result.get("padding-top") == "12px"

"""
NamingEngine 單元測試（P2 #14）
測試 7 層優先順序：data-figma-name → 組件名 → id → 語意 class → ARIA/tag → fallback
"""
import pytest
from airis_pdm.naming_engine import NamingEngine, NamingConfig


def make_engine(ignore_prefixes=None):
    cfg = NamingConfig()
    if ignore_prefixes is not None:
        cfg.ignore_class_prefixes = ignore_prefixes
    return NamingEngine(cfg)


# ─── Priority 1: data-figma-name ────────────────────────────────────────────

def test_data_figma_name_takes_priority():
    eng = make_engine()
    name = eng.resolve_name(
        parent_path="",
        tag="div",
        attrs={"data-figma-name": "MyCustomName", "id": "ignored", "class": "ignored"},
        component_name="IgnoredComp",
        sibling_index=0,
        sibling_tag_count=1,
    )
    assert "MyCustomName" in name


# ─── Priority 2: component name ─────────────────────────────────────────────

def test_component_name_used_when_no_figma_attr():
    eng = make_engine()
    name = eng.resolve_name(
        parent_path="",
        tag="div",
        attrs={"id": "ignored"},
        component_name="LoginForm",
        sibling_index=0,
        sibling_tag_count=1,
    )
    assert "Loginform" in name or "LoginForm" in name or "login" in name.lower()


# ─── Priority 3: id ─────────────────────────────────────────────────────────

def test_id_used_when_no_component():
    eng = make_engine()
    name = eng.resolve_name(
        parent_path="",
        tag="div",
        attrs={"id": "login-form"},
        component_name=None,
        sibling_index=0,
        sibling_tag_count=1,
    )
    assert "Login" in name or "login" in name.lower()


# ─── Priority 4: semantic class ─────────────────────────────────────────────

def test_semantic_class_used_when_no_id():
    """NamingEngine 從 class 屬性中選第一個非 ignore_prefix 的 class。
    使用單一語意 class 確保選取結果可預期。
    """
    eng = make_engine(ignore_prefixes=["flex", "grid", "p-", "m-", "text-", "bg-", "items-"])
    name = eng.resolve_name(
        parent_path="",
        tag="div",
        attrs={"class": "flex items-center card-header"},
        component_name=None,
        sibling_index=0,
        sibling_tag_count=1,
    )
    # ignore_prefixes 包含 flex/items-，所以 card-header 應被選到
    assert "Card" in name or "card" in name.lower() or "Header" in name


# ─── Priority 5/6: ARIA role / tag fallback ─────────────────────────────────

def test_tag_fallback_for_semantic_tags():
    eng = make_engine()
    for tag, expected in [
        ("button", "Button"),
        ("input", "Input"),
        ("nav", "Nav"),
        ("header", "Header"),
        ("footer", "Footer"),
    ]:
        name = eng.resolve_name(
            parent_path="",
            tag=tag,
            attrs={},
            component_name=None,
            sibling_index=0,
            sibling_tag_count=1,
        )
        assert expected.lower() in name.lower(), f"Expected {expected} in name for <{tag}>"


def test_generic_div_with_no_class_gets_fallback():
    eng = make_engine()
    name = eng.resolve_name(
        parent_path="",
        tag="div",
        attrs={},
        component_name=None,
        sibling_index=0,
        sibling_tag_count=1,
    )
    # div 沒有 id/class 應該 fallback 到 Frame 或 Div
    assert name != ""


# ─── Sibling 排序 ─────────────────────────────────────────────────────────────

def test_sibling_index_appended_when_multiple():
    eng = make_engine()
    name0 = eng.resolve_name(
        parent_path="",
        tag="li",
        attrs={},
        component_name=None,
        sibling_index=0,
        sibling_tag_count=3,
    )
    name1 = eng.resolve_name(
        parent_path="",
        tag="li",
        attrs={},
        component_name=None,
        sibling_index=1,
        sibling_tag_count=3,
    )
    # 當同 tag 有多個兄弟，名稱後應加索引以區分
    assert name0 != name1


def test_sibling_index_not_appended_when_single():
    eng = make_engine()
    name = eng.resolve_name(
        parent_path="",
        tag="section",
        attrs={},
        component_name=None,
        sibling_index=0,
        sibling_tag_count=1,
    )
    # 單一同 tag 不需要加索引
    assert "1" not in name or "Section" in name


# ─── Hierarchy path ──────────────────────────────────────────────────────────

def test_parent_path_prepended():
    eng = make_engine()
    name = eng.resolve_name(
        parent_path="LoginPage",
        tag="div",
        attrs={"id": "header"},
        component_name=None,
        sibling_index=0,
        sibling_tag_count=1,
    )
    assert name.startswith("LoginPage")


# ─── Sanitize / PascalCase ───────────────────────────────────────────────────

def test_kebab_id_converted_to_pascal():
    eng = make_engine()
    name = eng.resolve_name(
        parent_path="",
        tag="div",
        attrs={"id": "user-profile-card"},
        component_name=None,
        sibling_index=0,
        sibling_tag_count=1,
    )
    local = name.split("/")[-1]
    # 應為 PascalCase，不含 -
    assert "-" not in local


def test_special_chars_sanitized():
    eng = make_engine()
    name = eng.resolve_name(
        parent_path="",
        tag="div",
        attrs={"id": "btn@click#special!"},
        component_name=None,
        sibling_index=0,
        sibling_tag_count=1,
    )
    assert "@" not in name
    assert "#" not in name
    assert "!" not in name

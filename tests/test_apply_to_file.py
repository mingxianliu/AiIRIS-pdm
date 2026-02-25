"""
CodePatcher 實際寫檔整合測試（P4 #18）
測試 Tailwind / CSS / inline 三種策略真正讀寫本機檔案。
所有測試使用 tmp_path（pytest 暫存目錄），不汙染實際專案。
"""
import pytest
from pathlib import Path
from airis_pdm.code_patcher import CodePatcher, find_files_by_selector


# ─── helper ──────────────────────────────────────────────────────────────────

def make_patcher(name_mapping, strategy="tailwind", src_root="", dry_run=False):
    return CodePatcher(
        name_mapping=name_mapping,
        style_strategy=strategy,
        src_root=src_root,
        dry_run=dry_run,
    )


def make_diff(node_name, **props):
    """產生單一節點的 diff 字典。"""
    return {node_name: {k: {"before": None, "after": v} for k, v in props.items()}}


# ─── find_files_by_selector ───────────────────────────────────────────────────

class TestFindFilesBySelector:
    def test_find_by_id(self, tmp_path):
        f = tmp_path / "login.vue"
        f.write_text('<div id="login-form" class="container">', encoding="utf-8")
        result = find_files_by_selector(str(tmp_path), "#login-form", {".vue"})
        assert str(f) in result

    def test_find_by_class(self, tmp_path):
        f = tmp_path / "Button.tsx"
        f.write_text('<button class="btn btn-primary">Click</button>', encoding="utf-8")
        result = find_files_by_selector(str(tmp_path), ".btn-primary", {".tsx"})
        assert str(f) in result

    def test_no_match_returns_empty(self, tmp_path):
        f = tmp_path / "Empty.vue"
        f.write_text("<div></div>", encoding="utf-8")
        result = find_files_by_selector(str(tmp_path), "#nonexistent", {".vue"})
        assert result == []

    def test_nonexistent_src_root_returns_empty(self):
        result = find_files_by_selector("/nonexistent/path", "#foo")
        assert result == []

    def test_multiple_matches_returns_all(self, tmp_path):
        (tmp_path / "a.vue").write_text('<div id="header">', encoding="utf-8")
        (tmp_path / "b.vue").write_text('<div id="header">', encoding="utf-8")
        result = find_files_by_selector(str(tmp_path), "#header", {".vue"})
        assert len(result) == 2


# ─── Tailwind 寫檔 ───────────────────────────────────────────────────────────

class TestApplyTailwindToFile:
    def test_class_added_to_id_element(self, tmp_path):
        f = tmp_path / "App.vue"
        f.write_text('<div id="hero" class="container">', encoding="utf-8")

        mapping = {"Hero": {"selector": "#hero", "sourceFile": "http://localhost:5173"}}
        patcher = make_patcher(mapping, strategy="tailwind", src_root=str(tmp_path))

        diff = make_diff("Hero", **{"text.fontSize": 24})
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert "text-[24px]" in content

    def test_dry_run_does_not_write(self, tmp_path):
        f = tmp_path / "App.vue"
        original = '<div id="hero" class="container">'
        f.write_text(original, encoding="utf-8")

        mapping = {"Hero": {"selector": "#hero", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="tailwind", src_root=str(tmp_path), dry_run=True)

        diff = make_diff("Hero", **{"text.fontSize": 18})
        patcher.apply_changes(diff)

        # 檔案不應被修改
        assert f.read_text(encoding="utf-8") == original

    def test_class_added_by_class_selector(self, tmp_path):
        f = tmp_path / "Button.vue"
        f.write_text('<button class="btn btn-secondary">', encoding="utf-8")

        mapping = {"Btn": {"selector": ".btn-secondary", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="tailwind", src_root=str(tmp_path))

        diff = make_diff("Btn", **{"styles.opacity": 0.5})
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert "opacity-50" in content

    def test_multiple_classes_added(self, tmp_path):
        f = tmp_path / "Card.vue"
        f.write_text('<div id="card-body" class="p-4">', encoding="utf-8")

        mapping = {"CardBody": {"selector": "#card-body", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="tailwind", src_root=str(tmp_path))

        diff = make_diff("CardBody", **{
            "text.fontSize": 14,
            "text.fontWeight": 600,
        })
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert "text-[14px]" in content
        assert "font-semibold" in content


# ─── CSS 寫檔 ────────────────────────────────────────────────────────────────

class TestApplyCssToFile:
    def test_existing_selector_updated(self, tmp_path):
        f = tmp_path / "styles.css"
        f.write_text(".hero {\n  color: red;\n}\n", encoding="utf-8")

        mapping = {"Hero": {"selector": ".hero", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="css-modules", src_root=str(tmp_path))

        diff = make_diff("Hero", **{"text.fontSize": 20})
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert "font-size" in content
        assert "20px" in content

    def test_new_selector_appended(self, tmp_path):
        """當 CSS 檔案存在 selector 但無目標屬性時，應在現有 block 中插入屬性。"""
        f = tmp_path / "styles.css"
        # 檔案含有 .new-block 區塊（空的），_apply_css 將插入屬性
        f.write_text(".other { color: blue; }\n.new-block {\n}\n", encoding="utf-8")

        mapping = {"NewBlock": {"selector": ".new-block", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="css-modules", src_root=str(tmp_path))

        diff = make_diff("NewBlock", **{"autoLayout.spacing": 16})
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert ".new-block" in content
        assert "gap" in content


    def test_scss_file_found_by_extension(self, tmp_path):
        f = tmp_path / "component.scss"
        f.write_text(".card {\n  padding: 8px;\n}\n", encoding="utf-8")

        mapping = {"Card": {"selector": ".card", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="scss", src_root=str(tmp_path))

        diff = make_diff("Card", **{"styles.opacity": 0.8})
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert "opacity" in content

    def test_css_modules_file_found(self, tmp_path):
        f = tmp_path / "Button.module.css"
        f.write_text(".primary {\n  background: blue;\n}\n", encoding="utf-8")

        mapping = {"Primary": {"selector": ".primary", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="css-modules", src_root=str(tmp_path))

        diff = make_diff("Primary", **{"text.fontWeight": 700})
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert "font-weight" in content


# ─── inline 寫檔 ─────────────────────────────────────────────────────────────

class TestApplyInlineToFile:
    def test_style_attr_added(self, tmp_path):
        f = tmp_path / "index.html"
        f.write_text('<div id="banner"><h1>Hello</h1></div>', encoding="utf-8")

        mapping = {"Banner": {"selector": "#banner", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="inline", src_root=str(tmp_path))

        diff = make_diff("Banner", **{"styles.backgroundColor": "rgba(0, 0, 0, 1)"})
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert "style=" in content
        assert "background-color" in content

    def test_existing_style_attr_extended(self, tmp_path):
        f = tmp_path / "index.html"
        f.write_text('<div id="box" style="color: red;">', encoding="utf-8")

        mapping = {"Box": {"selector": "#box", "sourceFile": ""}}
        patcher = make_patcher(mapping, strategy="inline", src_root=str(tmp_path))

        diff = make_diff("Box", **{"text.fontSize": 16})
        patcher.apply_changes(diff)

        content = f.read_text(encoding="utf-8")
        assert "font-size" in content
        # 原有 style 不應消失
        assert "color" in content


# ─── config 驗證整合 ───────────────────────────────────────────────────────────

class TestValidateConfig:
    def test_valid_config_no_warnings(self, capsys):
        from airis_pdm.config import validate_config
        validate_config({
            "figma": {"personalAccessToken": "xxx", "fileKey": "yyy"},
            "source": {"framework": "vue", "styleStrategy": "tailwind", "srcRoot": "/tmp"},
            "viewport": {"width": 1440, "height": 900},
            "naming": {"separator": "/"},
            "export": {"snapshotDir": ".figma-sync"},
        })
        captured = capsys.readouterr()
        # 沒有未知欄位，只可能有 srcRoot 路徑警告
        assert "未知頂層欄位" not in captured.out

    def test_unknown_top_key_warns(self, capsys):
        from airis_pdm.config import validate_config
        validate_config({"unknownKey": "value"})
        captured = capsys.readouterr()
        assert "unknownKey" in captured.out

    def test_invalid_framework_warns(self, capsys):
        from airis_pdm.config import validate_config
        validate_config({"source": {"framework": "angular"}})
        captured = capsys.readouterr()
        assert "framework" in captured.out

    def test_invalid_viewport_type_warns(self, capsys):
        from airis_pdm.config import validate_config
        validate_config({"viewport": {"width": "1440px", "height": 900}})
        captured = capsys.readouterr()
        assert "viewport.width" in captured.out

    def test_empty_config_no_error(self, capsys):
        from airis_pdm.config import validate_config
        validate_config({})
        captured = capsys.readouterr()
        assert captured.out == ""

"""
FigmaToIR / IRDiffer / CodePatcher mock 測試（P2 #10）
不需要真實 Figma Token，全部用假資料。
"""
import pytest
from airis_pdm.figma_reader import FigmaToIR, IRDiffer
from airis_pdm.code_patcher import CodePatcher


# ─── FigmaToIR ───────────────────────────────────────────────────────────────

class TestFigmaToIR:
    def _make_node(self, **kwargs):
        base = {
            "type": "FRAME",
            "name": "TestFrame",
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 100},
            "children": [],
        }
        base.update(kwargs)
        return base

    def test_convert_basic_frame(self):
        node = self._make_node()
        result = FigmaToIR().convert(node)
        assert result["figmaName"] == "TestFrame"
        assert result["figmaType"] == "FRAME"
        assert result["layout"]["width"] == 100

    def test_convert_text_node(self):
        node = self._make_node(
            type="TEXT",
            name="Title",
            characters="Hello",
            style={"fontSize": 16, "fontFamily": "Inter", "fontWeight": 700},
            fills=[{"visible": True, "type": "SOLID", "color": {"r": 0, "g": 0, "b": 0, "a": 1}}],
        )
        result = FigmaToIR().convert(node)
        assert result["figmaType"] == "TEXT"
        assert result["text"]["characters"] == "Hello"
        assert result["text"]["fontSize"] == 16

    def test_convert_solid_fill(self):
        node = self._make_node(
            type="RECTANGLE",
            name="Box",
            fills=[{"visible": True, "type": "SOLID",
                    "color": {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0}}],
        )
        result = FigmaToIR().convert(node)
        assert "styles" in result
        assert "rgba(255, 0, 0" in result["styles"]["backgroundColor"]

    def test_convert_gradient_fill(self):
        node = self._make_node(
            type="RECTANGLE",
            name="GradBox",
            fills=[{
                "visible": True,
                "type": "GRADIENT_LINEAR",
                "gradientStops": [
                    {"color": {"r": 0.3, "g": 0.3, "b": 0.8, "a": 1.0}, "position": 0.0},
                    {"color": {"r": 0.8, "g": 0.3, "b": 0.3, "a": 1.0}, "position": 1.0},
                ],
            }],
        )
        result = FigmaToIR().convert(node)
        fills = result.get("styles", {}).get("fills", [])
        assert any(f["type"] == "GRADIENT_LINEAR" for f in fills)
        assert len(fills[0]["stops"]) == 2

    def test_convert_auto_layout(self):
        node = self._make_node(
            layoutMode="HORIZONTAL",
            itemSpacing=16,
            paddingTop=8, paddingRight=8, paddingBottom=8, paddingLeft=8,
            primaryAxisAlignItems="MIN",
            counterAxisAlignItems="CENTER",
        )
        result = FigmaToIR().convert(node)
        assert result["figmaType"] == "AUTO_LAYOUT"
        assert result["autoLayout"]["direction"] == "HORIZONTAL"
        assert result["autoLayout"]["spacing"] == 16

    def test_convert_layout_integrity_warning(self):
        """有子節點但無 Auto Layout 的 FRAME 應標記 _layoutWarning。"""
        node = self._make_node(
            children=[
                {"type": "RECTANGLE", "name": "Child",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 10, "height": 10},
                 "visible": True, "children": []}
            ]
        )
        result = FigmaToIR().convert(node)
        assert result.get("_layoutWarning") == "NO_AUTO_LAYOUT"

    def test_convert_invisible_children_excluded(self):
        node = self._make_node(
            children=[
                {"type": "RECTANGLE", "name": "Visible",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 10, "height": 10},
                 "visible": True, "children": []},
                {"type": "RECTANGLE", "name": "Hidden",
                 "absoluteBoundingBox": {"x": 0, "y": 0, "width": 10, "height": 10},
                 "visible": False, "children": []},
            ]
        )
        result = FigmaToIR().convert(node)
        assert len(result.get("children", [])) == 1
        assert result["children"][0]["figmaName"] == "Visible"

    def test_convert_drop_shadow(self):
        node = self._make_node(
            effects=[{
                "visible": True,
                "type": "DROP_SHADOW",
                "color": {"r": 0, "g": 0, "b": 0, "a": 0.25},
                "offset": {"x": 0, "y": 4},
                "radius": 8,
                "spread": 0,
            }]
        )
        result = FigmaToIR().convert(node)
        shadows = result.get("styles", {}).get("shadow", [])
        assert len(shadows) == 1
        assert shadows[0]["blur"] == 8


# ─── IRDiffer ────────────────────────────────────────────────────────────────

class TestIRDiffer:
    def _make_ir(self, name="Node", bg="rgba(255,0,0,1)", children=None):
        return {
            "figmaName": name,
            "figmaType": "FRAME",
            "layout": {"width": 100, "height": 100},
            "styles": {"backgroundColor": bg},
            "children": children or [],
        }

    def test_no_changes(self):
        ir = self._make_ir()
        changes = IRDiffer().diff(ir, ir)
        assert changes == {}

    def test_style_changed(self):
        before = self._make_ir(bg="rgba(255,0,0,1)")
        after = self._make_ir(bg="rgba(0,0,255,1)")
        changes = IRDiffer().diff(before, after)
        assert "Node" in changes
        assert "styles.backgroundColor" in changes["Node"]

    def test_node_added(self):
        before = self._make_ir()
        after = self._make_ir(children=[self._make_ir("Child")])
        changes = IRDiffer().diff(before, after)
        assert any("Child" in k for k in changes)
        child_key = next(k for k in changes if "Child" in k)
        assert changes[child_key]["_status"] == "added"

    def test_node_deleted(self):
        before = self._make_ir(children=[self._make_ir("Child")])
        after = self._make_ir()
        changes = IRDiffer().diff(before, after)
        child_key = next(k for k in changes if "Child" in k)
        assert changes[child_key]["_status"] == "deleted"

    def test_layout_size_change(self):
        before = self._make_ir()
        after = {**before, "layout": {"width": 200, "height": 100}}
        changes = IRDiffer().diff(before, after)
        assert "layout.width" in changes.get("Node", {})

    def test_layout_integrity_warning(self):
        before = self._make_ir()
        after = {**before, "_layoutWarning": "NO_AUTO_LAYOUT"}
        changes = IRDiffer().diff(before, after)
        assert "layout.integrity" in changes.get("Node", {})


# ─── CodePatcher (dry_run mode) ───────────────────────────────────────────────

class TestCodePatcher:
    def _patcher(self, mapping=None, strategy="tailwind"):
        return CodePatcher(
            name_mapping=mapping or {},
            style_strategy=strategy,
            src_root="",
            dry_run=True,  # 不實際寫檔
        )

    def test_generate_report_changed(self):
        patcher = self._patcher({"Button": {"selector": ".btn", "sourceFile": ""}})
        diff = {"Button": {"styles.backgroundColor": {"before": "red", "after": "blue"}}}
        report = patcher.generate_patch_report(diff)
        assert "CHANGED: Button" in report
        assert "styles.backgroundColor" in report

    def test_generate_report_added(self):
        patcher = self._patcher()
        diff = {"NewNode": {"_status": "added"}}
        report = patcher.generate_patch_report(diff)
        assert "NEW: NewNode" in report

    def test_generate_report_deleted(self):
        patcher = self._patcher()
        diff = {"OldNode": {"_status": "deleted"}}
        report = patcher.generate_patch_report(diff)
        assert "DEL: OldNode" in report

    def test_apply_skips_added_deleted(self):
        patcher = self._patcher()
        diff = {
            "A": {"_status": "added"},
            "B": {"_status": "deleted"},
        }
        summary = patcher.apply_changes(diff)
        assert summary == {}

    def test_apply_no_mapping_returns_empty(self):
        patcher = self._patcher(mapping={})
        diff = {"UnknownNode": {"styles.backgroundColor": {"before": "red", "after": "blue"}}}
        summary = patcher.apply_changes(diff)
        assert summary == {}

    def test_apply_dry_run_message(self):
        patcher = self._patcher(
            mapping={"Btn": {"selector": "#my-btn", "sourceFile": "http://localhost:5173"}}
        )
        diff = {"Btn": {"text.fontSize": {"before": 14, "after": 18}}}
        summary = patcher.apply_changes(diff)
        # dry_run=True + 找不到實際檔案，應回傳包含 selector 的說明訊息
        all_lines = [line for lines in summary.values() for line in lines]
        assert any("#my-btn" in line or "DRY" in line or "找不到" in line for line in all_lines)

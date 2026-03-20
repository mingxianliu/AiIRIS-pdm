from airis_pdm.figmai import validate_ui_ir


def test_validate_ui_ir_autofix_empty():
    result = validate_ui_ir(None)
    assert result.valid is False
    assert result.fixed["type"] == "frame"
    assert isinstance(result.fixed["children"], list)


def test_validate_ui_ir_root_text_fixed():
    root = {
        "name": "Title",
        "type": "text",
        "sourceType": "TEXT",
        "layout": {"x": 1, "y": 2, "width": 3, "height": 4},
        "children": [],
        "text": {"characters": "Hi"},
    }
    result = validate_ui_ir(root)
    assert result.fixed["type"] == "frame"
    assert result.fixed["sourceType"] == "FRAME"


def test_validate_ui_ir_text_characters_fixed():
    root = {
        "name": "Root",
        "type": "frame",
        "sourceType": "FRAME",
        "layout": {"x": 0, "y": 0, "width": 0, "height": 0},
        "children": [
            {
                "name": "Label",
                "type": "text",
                "sourceType": "TEXT",
                "layout": {"x": 0, "y": 0, "width": 10, "height": 10},
                "children": [],
                "text": {"characters": 123},
            }
        ],
    }
    result = validate_ui_ir(root)
    txt = result.fixed["children"][0]["text"]["characters"]
    assert isinstance(txt, str)

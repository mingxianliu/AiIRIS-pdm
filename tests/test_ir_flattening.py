import pytest
from airis_pdm.ir_builder import IRBuilderV2

def test_smart_flatten_basic():
    builder = IRBuilderV2(smart_flatten=True)
    
    # Structure: Root -> UselessWrapper -> Child
    raw_tree = {
        "tag": "div",
        "attrs": {"id": "root"},
        "children": [
            {
                "tag": "div",
                "attrs": {}, # No ID, no name
                "styles": {}, # No styles
                "children": [
                    {
                        "tag": "button",
                        "attrs": {"id": "btn"},
                        "styles": {"backgroundColor": "red"},
                        "children": []
                    }
                ]
            }
        ]
    }
    
    ir = builder.build(raw_tree, {"width": 100, "height": 100})
    root = ir["tree"]
    
    # Root should have "btn" as direct child, skipping the wrapper
    assert len(root["children"]) == 1
    child = root["children"][0]
    assert child["htmlTag"] == "button"
    assert child["figmaName"] == "Btn"

def test_smart_flatten_negative_style():
    builder = IRBuilderV2(smart_flatten=True)
    
    # Structure: Root -> Wrapper(bg=red) -> Child
    raw_tree = {
        "tag": "div",
        "attrs": {"id": "root"},
        "children": [
            {
                "tag": "div",
                "attrs": {},
                "styles": {"backgroundColor": "red"}, # Has style!
                "children": [
                    {
                        "tag": "button",
                        "children": []
                    }
                ]
            }
        ]
    }
    
    ir = builder.build(raw_tree, {"width": 100, "height": 100})
    root = ir["tree"]
    
    # Should NOT flatten
    assert len(root["children"]) == 1
    wrapper = root["children"][0]
    assert wrapper["htmlTag"] == "div"
    assert len(wrapper["children"]) == 1
    assert wrapper["children"][0]["htmlTag"] == "button"

def test_smart_flatten_negative_multiple_children():
    builder = IRBuilderV2(smart_flatten=True)
    
    # Structure: Root -> Wrapper -> [Child1, Child2]
    raw_tree = {
        "tag": "div",
        "attrs": {"id": "root"},
        "children": [
            {
                "tag": "div",
                "attrs": {},
                "styles": {},
                "children": [
                    {"tag": "span", "children": []},
                    {"tag": "span", "children": []}
                ]
            }
        ]
    }
    
    ir = builder.build(raw_tree, {"width": 100, "height": 100})
    root = ir["tree"]
    
    # Should NOT flatten
    wrapper = root["children"][0]
    assert wrapper["htmlTag"] == "div"
    assert len(wrapper["children"]) == 2

def test_smart_flatten_negative_component():
    builder = IRBuilderV2(smart_flatten=True)
    
    # Structure: Root -> Wrapper(component=MyComp) -> Child
    raw_tree = {
        "tag": "div",
        "attrs": {"id": "root"},
        "children": [
            {
                "tag": "div",
                "componentName": "MyComp", # Is component!
                "attrs": {},
                "styles": {},
                "children": [
                    {"tag": "button", "children": []}
                ]
            }
        ]
    }
    
    ir = builder.build(raw_tree, {"width": 100, "height": 100})
    root = ir["tree"]
    
    # Should NOT flatten
    wrapper = root["children"][0]
    assert wrapper["figmaName"] == "Mycomp"
    assert wrapper["htmlTag"] == "div"

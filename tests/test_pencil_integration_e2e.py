import pytest
import os
import json
import shutil
from airis_pdm.pencil_mcp_tools import PencilMcpTools

@pytest.fixture
def clean_generated():
    output_dir = "./generated_test_pencil"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    yield output_dir
    # Keep for inspection if needed, or cleanup
    # shutil.rmtree(output_dir)

def test_pencil_to_code_generation(clean_generated):
    output_dir = clean_generated
    tools = PencilMcpTools(output_dir=output_dir)
    
    # Simulating data from mcp_pencil_batch_get
    pen_data = [
        {
            "id": "bi8Au",
            "type": "frame",
            "name": "BadgeContainer",
            "children": [
                {
                    "id": "s1HDq",
                    "type": "frame",
                    "name": "Badge/Active",
                    "fill": "#E6F4EA",
                    "padding": 8,
                    "children": [
                        {
                            "id": "BIBZz",
                            "type": "text",
                            "content": "ACTIVE",
                            "fill": "#137333",
                            "fontSize": 12
                        }
                    ]
                }
            ]
        }
    ]
    
    # 1. Generate code
    result_json = tools.generate_code_from_pen(pen_data, target="vue")
    result = json.loads(result_json)
    
    assert result["status"] == "ok"
    assert any("BadgeContainer.vue" in f for f in result["data"]["generated_files"])
    
    # 2. Check generated file content
    vue_file = os.path.join(output_dir, "pages", "BadgeContainer.vue")
    assert os.path.exists(vue_file)
    
    with open(vue_file, "r") as f:
        content = f.read()
        assert "ACTIVE" in content
        # Check if color is translated correctly
        # Note: PencilMcpTools -> PencilToIR -> IR -> Generator
        # PencilToIR normalizes #E6F4EA to rgba
        assert "background-color" in content
        
    print("\n[Success] Pencil to Vue code generation verified!")

def test_pencil_design_compliance(clean_generated):
    tools = PencilMcpTools(output_dir=clean_generated)
    
    # Design with issues (missing Auto Layout)
    pen_data = [
        {
            "id": "root",
            "type": "frame",
            "name": "NonLayoutFrame",
            "layout": "none",
            "children": [
                 {"id": "c1", "type": "frame", "children": []}
            ]
        }
    ]
    
    result_json = tools.validate_design_system_compliance(pen_data)
    result = json.loads(result_json)
    
    assert result["status"] == "ok"
    assert result["data"]["score"] < 100
    assert any("缺少 Auto Layout" in iss for iss in result["data"]["issues"])
    print("\n[Success] Design compliance check verified!")

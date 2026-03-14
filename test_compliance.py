
import asyncio
import json
import os
from airis_pdm.pencil_mcp_tools import PencilMcpTools

def test():
    tools = PencilMcpTools(output_dir="/Users/erich/Documents/GitHub/AiIRIS-pdm/test_visual")
    
    ref_path = "/Users/erich/Documents/GitHub/AiIRIS-pdm/test_visual/s1HDq.png"
    live_url = "http://localhost:8080"
    
    print(f"Running visual compliance for {live_url} against {ref_path}...")
    
    # 直接呼叫，內部會處理 asyncio.run
    result = tools.run_visual_compliance(
        reference_image_path=ref_path,
        live_url=live_url,
        pixel_diff_threshold=0.05,
        viewport_width=400,
        viewport_height=200,
        run_root_cause_on_failure=True,
        workspace_id="visual_test_ws"
    )
    
    print("Result:")
    print(json.dumps(json.loads(result), indent=2, ensure_ascii=False))
    
if __name__ == "__main__":
    test()

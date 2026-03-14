
import asyncio
import json
import os
from airis_pdm.pencil_mcp_tools import PencilMcpTools

async def test():
    tools = PencilMcpTools(output_dir="/Users/erich/Documents/GitHub/AiIRIS-pdm/dashboard_gen")
    
    # 這裡我們模擬從 batch_get 取得的資料
    pen_data = [
        {
            "id": "s1HDq",
            "name": "Badge/Active",
            "type": "frame",
            "fill": "#E6F4EA",
            "cornerRadius": 4,
            "padding": 8,
            "gap": 4,
            "children": [
                {
                    "id": "BIBZz",
                    "type": "text",
                    "content": "ACTIVE",
                    "fill": "#137333",
                    "fontFamily": "Inter",
                    "fontSize": 12,
                    "fontWeight": "700"
                }
            ],
            "x": 0,
            "y": 0
        }
    ]
    
    print("Generating code...")
    gen_res = tools.generate_code_from_pen(pen_data, target="html")
    print(gen_res)
    
if __name__ == "__main__":
    asyncio.run(test())

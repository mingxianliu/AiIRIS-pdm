import pytest
import os
import json
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

def test_figma_plugin_import_flow(browser_context):
    page = browser_context.new_page()
    html_path = "file://" + os.path.abspath("/Users/erich/Documents/GitHub/AiIRIS-pdm/figma_plugin/src/ui.html")
    page.goto(html_path)

    # 1. Check initial state
    import_btn = page.locator("#importBtn")
    assert import_btn.is_disabled()

    # 2. Mock parent.postMessage to capture plugin messages
    page.evaluate("""
        window.messageLog = [];
        window.parent.postMessage = (msg, targetOrigin) => {
            if (msg && msg.pluginMessage) {
                window.messageLog.push(msg.pluginMessage);
            }
        };
    """)

    # 3. Paste valid IR JSON
    sample_ir = {
        "figmaName": "Main Screen",
        "figmaType": "FRAME",
        "children": [
            {"figmaName": "Header", "figmaType": "RECTANGLE", "children": []},
            {"figmaName": "Label", "figmaType": "TEXT", "text": {"characters": "Welcome"}, "children": []}
        ]
    }
    
    page.fill("#jsonInput", json.dumps(sample_ir))
    # Give it a tiny bit of time to parse JSON
    page.wait_for_timeout(100)
    
    # Wait for JS to process ('parsePayload' is triggered on input)
    # The status message should show success
    status = page.locator("#status")
    assert "Payload loaded: 3 nodes" in status.inner_text()
    assert import_btn.is_enabled()

    # 4. Click Preview and check tree
    page.click("button:has-text('Preview Names')")
    preview = page.locator("#treePreview")
    assert "Main Screen" in preview.inner_text()
    assert "Header" in preview.inner_text()
    assert "Welcome" in preview.inner_text()

    # 5. Click Import and verify message sent to parent
    page.click("#importBtn")
    
    # Check captured messages
    messages = page.evaluate("window.messageLog")
    assert len(messages) > 0
    assert messages[-1]["type"] == "import-ir"
    assert messages[-1]["payload"]["figmaName"] == "Main Screen"

    # 6. Simulate 'import-complete' message from Figma back to UI
    # Directly call the handler to avoid event loop / origin issues in file:// context
    page.evaluate("""
        window.onmessage({ 
            data: { 
                pluginMessage: { type: 'import-complete', nodeCount: 3 } 
            } 
        });
    """)
    
    # Check if UI updated status
    assert "Import complete! 3 nodes" in status.inner_text()
    
    page.close()

def test_figma_plugin_tabs(browser_context):
    page = browser_context.new_page()
    html_path = "file://" + os.path.abspath("/Users/erich/Documents/GitHub/AiIRIS-pdm/figma_plugin/src/ui.html")
    page.goto(html_path)

    # Switch to Export tab
    page.click("text=Export")
    
    # Check if export tab is active
    export_content = page.locator("#tab-export")
    assert "active" in export_content.get_attribute("class")
    assert export_content.is_visible()
    
    # Verify the export button is there
    export_btn = page.locator("button:has-text('Export Selection')")
    assert export_btn.is_visible()
    
    page.close()

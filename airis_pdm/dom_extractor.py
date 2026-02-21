"""
DOM 擷取 — Playwright 無頭瀏覽器擷取 Vue/React/HTML 頁面

擷取 DOM 樹、computed styles、邊界、文字與組件邊界，供 IR 建構使用。
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractionConfig:
    """DOM 擷取設定."""
    viewport_width: int = 1440
    viewport_height: int = 900
    wait_for_selector: Optional[str] = None
    wait_timeout_ms: int = 10000
    root_selector: str = "#app, #root, #__nuxt, body"
    skip_invisible: bool = True
    max_depth: int = 50
    capture_images: bool = True
    detect_components: bool = True
    framework: str = "vue"  # "vue" | "react" | "html"


DOM_WALKER_JS = """
(config) => {
    const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'LINK', 'META', 'NOSCRIPT', 'BR', 'WBR']);
    const INLINE_TAGS = new Set(['SPAN', 'A', 'STRONG', 'EM', 'B', 'I', 'U', 'CODE', 'SMALL', 'SUB', 'SUP']);

    function parseColor(cssColor) {
        if (!cssColor || cssColor === 'transparent' || cssColor === 'rgba(0, 0, 0, 0)') return null;
        return cssColor;
    }

    function parseBorderRadius(styles) {
        const tl = parseFloat(styles.borderTopLeftRadius) || 0;
        const tr = parseFloat(styles.borderTopRightRadius) || 0;
        const br = parseFloat(styles.borderBottomRightRadius) || 0;
        const bl = parseFloat(styles.borderBottomLeftRadius) || 0;
        if (tl === 0 && tr === 0 && br === 0 && bl === 0) return null;
        return { topLeft: tl, topRight: tr, bottomRight: br, bottomLeft: bl };
    }

    function parseShadow(shadowStr) {
        if (!shadowStr || shadowStr === 'none') return null;
        const shadows = [];
        const parts = shadowStr.split(/,(?![^(]*\\))/);
        for (const part of parts) {
            const match = part.trim().match(
                /(?:inset\\s+)?(-?[\\d.]+)px\\s+(-?[\\d.]+)px\\s+(-?[\\d.]+)px\\s*(-?[\\d.]+)?px?\\s*(.*)/
            );
            if (match) {
                shadows.push({
                    offsetX: parseFloat(match[1]),
                    offsetY: parseFloat(match[2]),
                    blur: parseFloat(match[3]),
                    spread: parseFloat(match[4]) || 0,
                    color: match[5]?.trim() || 'rgba(0,0,0,0.25)'
                });
            }
        }
        return shadows.length > 0 ? shadows : null;
    }

    function detectFlexDirection(styles) {
        if (styles.display === 'flex' || styles.display === 'inline-flex') {
            const dir = styles.flexDirection || 'row';
            return dir.startsWith('column') ? 'VERTICAL' : 'HORIZONTAL';
        }
        return null;
    }

    function detectAlignment(styles) {
        const justify = styles.justifyContent || 'flex-start';
        const align = styles.alignItems || 'stretch';
        const primaryMap = {
            'flex-start': 'MIN', 'start': 'MIN', 'center': 'CENTER',
            'flex-end': 'MAX', 'end': 'MAX', 'space-between': 'SPACE_BETWEEN',
            'space-around': 'SPACE_BETWEEN', 'space-evenly': 'SPACE_BETWEEN',
        };
        const counterMap = {
            'flex-start': 'MIN', 'start': 'MIN', 'center': 'CENTER',
            'flex-end': 'MAX', 'end': 'MAX', 'stretch': 'STRETCH', 'baseline': 'MIN',
        };
        return {
            primary: primaryMap[justify] || 'MIN',
            counter: counterMap[align] || 'MIN'
        };
    }

    function getVueComponentName(el) {
        if (el.__vueParentComponent) {
            const comp = el.__vueParentComponent;
            return comp.type?.name || comp.type?.__name || null;
        }
        if (el.__vue__) return el.__vue__.$options?.name || null;
        return null;
    }

    function getReactComponentName(el) {
        const fiberKey = Object.keys(el).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$'));
        if (fiberKey) {
            let fiber = el[fiberKey];
            while (fiber) {
                if (fiber.type && typeof fiber.type === 'function')
                    return fiber.type.displayName || fiber.type.name || null;
                if (fiber.type && typeof fiber.type === 'object' && fiber.type.$$typeof)
                    return fiber.type.displayName || fiber.type.render?.displayName || fiber.type.render?.name || null;
                fiber = fiber.return;
            }
        }
        return null;
    }

    function getComponentName(el, framework) {
        const explicit = el.getAttribute('data-figma-component');
        if (explicit) return explicit;
        if (framework === 'vue') return getVueComponentName(el);
        if (framework === 'react') return getReactComponentName(el);
        return null;
    }

    function isTextOnlyNode(el) {
        const children = el.childNodes;
        for (let i = 0; i < children.length; i++) {
            if (children[i].nodeType === Node.ELEMENT_NODE && !INLINE_TAGS.has(children[i].tagName)) return false;
        }
        for (let i = 0; i < children.length; i++) {
            if (children[i].nodeType === Node.TEXT_NODE && children[i].textContent.trim()) return true;
        }
        return false;
    }

    function collectAttributes(el) {
        const attrs = {};
        for (const attr of el.attributes) attrs[attr.name] = attr.value;
        return attrs;
    }

    function getSiblingInfo(el) {
        const parent = el.parentElement;
        if (!parent) return { index: 0, tagCount: 1 };
        let index = 0, tagCount = 0;
        for (const child of parent.children) {
            if (child.tagName === el.tagName) {
                if (child === el) index = tagCount;
                tagCount++;
            }
        }
        return { index, tagCount };
    }

    function walkDOM(el, depth = 0) {
        if (depth > config.maxDepth) return null;
        if (SKIP_TAGS.has(el.tagName)) return null;
        const styles = window.getComputedStyle(el);
        if (config.skipInvisible) {
            if (styles.display === 'none') return null;
            if (styles.visibility === 'hidden' && !el.children.length) return null;
        }
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0 && !el.children.length) return null;

        const flexDir = detectFlexDirection(styles);
        const alignment = detectAlignment(styles);
        const siblingInfo = getSiblingInfo(el);

        const node = {
            tag: el.tagName.toLowerCase(),
            attrs: collectAttributes(el),
            componentName: config.detectComponents ? getComponentName(el, config.framework) : null,
            siblingIndex: siblingInfo.index,
            siblingTagCount: siblingInfo.tagCount,
            layout: { x: rect.x, y: rect.y, width: Math.max(rect.width, 1), height: Math.max(rect.height, 1) },
            isTextNode: isTextOnlyNode(el),
            textContent: isTextOnlyNode(el) ? (el.innerText || el.textContent || '') : null,
            isImage: el.tagName === 'IMG' || el.tagName === 'SVG' || (styles.backgroundImage && styles.backgroundImage !== 'none'),
            imageSrc: el.tagName === 'IMG' ? el.src : null,
            styles: {
                backgroundColor: parseColor(styles.backgroundColor),
                opacity: parseFloat(styles.opacity),
                borderRadius: parseBorderRadius(styles),
                borderColor: parseColor(styles.borderColor),
                borderWidth: parseFloat(styles.borderWidth) || 0,
                borderStyle: styles.borderStyle,
                shadow: parseShadow(styles.boxShadow),
                fontSize: parseFloat(styles.fontSize),
                fontFamily: styles.fontFamily?.split(',')[0]?.trim()?.replace(/['"]/g, ''),
                fontWeight: parseInt(styles.fontWeight) || 400,
                lineHeight: parseFloat(styles.lineHeight) || null,
                letterSpacing: parseFloat(styles.letterSpacing) || 0,
                textAlign: styles.textAlign,
                color: parseColor(styles.color),
            },
            autoLayout: flexDir ? {
                direction: flexDir,
                spacing: parseFloat(styles.gap) || parseFloat(styles.columnGap) || 0,
                paddingTop: parseFloat(styles.paddingTop) || 0,
                paddingRight: parseFloat(styles.paddingRight) || 0,
                paddingBottom: parseFloat(styles.paddingBottom) || 0,
                paddingLeft: parseFloat(styles.paddingLeft) || 0,
                primaryAlign: alignment.primary,
                counterAlign: alignment.counter,
                wrap: styles.flexWrap === 'wrap',
            } : null,
            children: []
        };

        if (!node.isTextNode) {
            for (const child of el.children) {
                const childNode = walkDOM(child, depth + 1);
                if (childNode) node.children.push(childNode);
            }
        }
        return node;
    }

    const selectors = config.rootSelector.split(',').map(s => s.trim());
    let root = null;
    for (const sel of selectors) {
        root = document.querySelector(sel);
        if (root) break;
    }
    if (!root) root = document.body;
    return walkDOM(root);
}
"""


async def extract_dom_tree(
    url: str,
    config: Optional[ExtractionConfig] = None,
) -> dict:
    """啟動無頭瀏覽器、開啟 URL、擷取 DOM 樹（回傳 raw tree，尚未轉 IR）。"""
    config = config or ExtractionConfig()
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError(
            "請先安裝 playwright： pip install playwright && playwright install chromium"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": config.viewport_width, "height": config.viewport_height}
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=config.wait_timeout_ms)
        if config.wait_for_selector:
            await page.wait_for_selector(config.wait_for_selector, timeout=config.wait_timeout_ms)
        await page.wait_for_timeout(500)

        js_config = {
            "rootSelector": config.root_selector,
            "skipInvisible": config.skip_invisible,
            "maxDepth": config.max_depth,
            "detectComponents": config.detect_components,
            "framework": config.framework,
        }
        raw_tree = await page.evaluate(DOM_WALKER_JS, js_config)
        screenshot_bytes = await page.screenshot(full_page=False)
        await browser.close()

    return {
        "tree": raw_tree,
        "screenshot": screenshot_bytes,
        "viewport": {"width": config.viewport_width, "height": config.viewport_height},
    }


def extract_dom_tree_sync(url: str, config: Optional[ExtractionConfig] = None) -> dict:
    """extract_dom_tree 的同步包裝."""
    return asyncio.run(extract_dom_tree(url, config))

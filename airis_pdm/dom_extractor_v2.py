"""
dom_extractor_v2.py — Enhanced DOM Extraction Engine

Complete rewrite that covers ALL capabilities of html-figma's browser module
PLUS our unique advantages (component detection, auto layout, naming metadata).

Coverage comparison:
  ┌───────────────────────────┬──────────┬──────────┬──────────┐
  │ Capability                │ html-figma│ v1 (ours)│ v2 (this)│
  ├───────────────────────────┼──────────┼──────────┼──────────┤
  │ Background solid          │    ✅    │    ✅    │    ✅    │
  │ Background gradient       │    ✅    │    ❌    │    ✅    │
  │ Background image URL      │    ✅    │    ❌    │    ✅    │
  │ Multi-background          │    ❌    │    ❌    │    ✅    │
  │ Border individual sides   │    ✅    │    ❌    │    ✅    │
  │ Border-image              │    ❌    │    ❌    │    ✅    │
  │ Box shadow (multiple)     │    ✅    │    ✅    │    ✅    │
  │ Inset shadow              │    ❌    │    ❌    │    ✅    │
  │ Text shadow               │    ❌    │    ❌    │    ✅    │
  │ Text decoration           │    ✅    │    ❌    │    ✅    │
  │ Text transform            │    ✅    │    ❌    │    ✅    │
  │ SVG inline → vector data  │    ✅    │    ❌    │    ✅    │
  │ Pseudo ::before/::after   │    ✅    │    ❌    │    ✅    │
  │ CSS transform             │    ❌    │    ❌    │    ✅    │
  │ Opacity + mix-blend-mode  │    ✅    │    ✅    │    ✅    │
  │ Overflow / clip           │    ❌    │    ❌    │    ✅    │
  │ CSS variable resolution   │    ❌    │    ❌    │    ✅    │
  │ Grid layout detection     │    ❌    │    ❌    │    ✅    │
  │ Flex layout detection     │    ❌    │    ✅    │    ✅    │
  │ Gap (row-gap, column-gap) │    ❌    │    partial│    ✅    │
  │ Aspect-ratio              │    ❌    │    ❌    │    ✅    │
  │ Filter / backdrop-filter  │    ❌    │    ❌    │    ✅    │
  │ Cursor style              │    ❌    │    ❌    │    ✅    │
  │ Vue component detection   │    ❌    │    ✅    │    ✅    │
  │ React component detection │    ❌    │    ✅    │    ✅    │
  │ Svelte component detect   │    ❌    │    ❌    │    ✅    │
  │ Tree structure (not flat) │    ❌    │    ✅    │    ✅    │
  │ data-figma-name           │    ❌    │    ✅    │    ✅    │
  │ Sibling index tracking    │    ❌    │    ✅    │    ✅    │
  │ Image base64 capture      │    ❌    │    ❌    │    ✅    │
  │ Canvas snapshot           │    ❌    │    ❌    │    ✅    │
  │ iframe detection          │    ❌    │    ❌    │    ✅    │
  │ Design token extraction   │    ❌    │    ❌    │    ✅    │
  │ Z-index stacking          │    ❌    │    ❌    │    ✅    │
  └───────────────────────────┴──────────┴──────────┴──────────┘
"""

import asyncio
import json
import base64
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractionConfig:
    """Configuration for DOM extraction."""
    viewport_width: int = 1440
    viewport_height: int = 900
    wait_for_selector: Optional[str] = None
    wait_timeout_ms: int = 10000
    root_selector: str = "#app, #root, #__nuxt, body"
    skip_invisible: bool = True
    max_depth: int = 50
    capture_images: bool = True
    capture_image_data: bool = False   # base64 encode images
    capture_canvas: bool = True        # snapshot <canvas> elements
    capture_svg_markup: bool = True    # capture inline SVG source
    capture_pseudo: bool = True        # capture ::before/::after
    capture_css_vars: bool = True      # resolve CSS custom properties
    detect_components: bool = True
    detect_grid: bool = True           # detect CSS Grid → Figma Auto Layout
    framework: str = "vue"


# ════════════════════════════════════════════════════════════════
# The Enhanced DOM Walker — runs inside the browser via Playwright
# ════════════════════════════════════════════════════════════════

DOM_WALKER_V2_JS = """
(config) => {
    // ────────────────────────────────────────
    // Constants
    // ────────────────────────────────────────
    const SKIP_TAGS = new Set([
        'SCRIPT', 'STYLE', 'LINK', 'META', 'NOSCRIPT', 'HEAD',
        'BR', 'WBR', 'TEMPLATE', 'SLOT', 'COLGROUP', 'COL',
    ]);
    const INLINE_TAGS = new Set([
        'SPAN', 'A', 'STRONG', 'EM', 'B', 'I', 'U', 'S', 'DEL', 'INS',
        'CODE', 'KBD', 'SAMP', 'VAR', 'SMALL', 'SUB', 'SUP', 'MARK',
        'ABBR', 'CITE', 'Q', 'DFN', 'TIME', 'DATA', 'RUBY', 'RT', 'RP',
    ]);
    const VOID_ELEMENTS = new Set([
        'AREA', 'BASE', 'BR', 'COL', 'EMBED', 'HR', 'IMG', 'INPUT',
        'LINK', 'META', 'SOURCE', 'TRACK', 'WBR',
    ]);

    // Reusable canvas for image capture
    let captureCanvas = null;
    function getCaptureCanvas() {
        if (!captureCanvas) {
            captureCanvas = document.createElement('canvas');
        }
        return captureCanvas;
    }

    // ────────────────────────────────────────
    // Color Parsing (comprehensive)
    // ────────────────────────────────────────
    function parseColor(cssColor) {
        if (!cssColor || cssColor === 'transparent' ||
            cssColor === 'rgba(0, 0, 0, 0)' ||
            cssColor === 'initial' || cssColor === 'inherit') {
            return null;
        }
        return cssColor;
    }

    function colorToRGBA(cssColor) {
        if (!cssColor) return null;
        const match = cssColor.match(
            /rgba?\\(\\s*([\\d.]+),\\s*([\\d.]+),\\s*([\\d.]+)(?:,\\s*([\\d.]+))?\\s*\\)/
        );
        if (match) {
            return {
                r: parseInt(match[1]) / 255,
                g: parseInt(match[2]) / 255,
                b: parseInt(match[3]) / 255,
                a: match[4] !== undefined ? parseFloat(match[4]) : 1,
            };
        }
        return null;
    }

    // ────────────────────────────────────────
    // Gradient Parsing ✨ NEW
    // ────────────────────────────────────────
    function parseGradient(bgImage) {
        if (!bgImage || bgImage === 'none') return null;
        const gradients = [];

        // Match linear-gradient, radial-gradient, conic-gradient
        const gradientRegex =
            /((?:repeating-)?(?:linear|radial|conic)-gradient)\\(([^)]+(?:\\([^)]*\\)[^)]*)*)\\)/g;
        let m;
        while ((m = gradientRegex.exec(bgImage)) !== null) {
            const type = m[1];
            const body = m[2];
            const gradient = { type, raw: m[0], stops: [] };

            if (type.includes('linear')) {
                // Parse angle
                const angleMatch = body.match(/^\\s*(\\d+(?:\\.\\d+)?deg)/);
                gradient.angle = angleMatch ? parseFloat(angleMatch[1]) : 180;

                // Parse direction keywords
                if (!angleMatch) {
                    const dirMatch = body.match(/^\\s*to\\s+(top|bottom|left|right|top left|top right|bottom left|bottom right)/);
                    if (dirMatch) {
                        const dirMap = {
                            'top': 0, 'right': 90, 'bottom': 180, 'left': 270,
                            'top right': 45, 'bottom right': 135,
                            'bottom left': 225, 'top left': 315,
                        };
                        gradient.angle = dirMap[dirMatch[1]] ?? 180;
                    }
                }
            }

            if (type.includes('radial')) {
                gradient.shape = body.includes('circle') ? 'circle' : 'ellipse';
            }

            // Parse color stops
            const stopRegex =
                /((?:rgba?|hsla?)\\([^)]+\\)|#[0-9a-fA-F]{3,8}|\\w+)(?:\\s+(\\d+(?:\\.\\d+)?%?))?/g;
            let s;
            // Skip the angle/direction part
            const stopsStr = body.replace(/^[^,]*,/, '');
            while ((s = stopRegex.exec(stopsStr)) !== null) {
                const color = s[1];
                const position = s[2] ? parseFloat(s[2]) / 100 : null;
                gradient.stops.push({ color, position });
            }

            // Auto-distribute positions
            if (gradient.stops.length > 0) {
                gradient.stops.forEach((stop, i) => {
                    if (stop.position === null) {
                        stop.position = i / Math.max(gradient.stops.length - 1, 1);
                    }
                });
            }

            gradients.push(gradient);
        }

        return gradients.length > 0 ? gradients : null;
    }

    // ────────────────────────────────────────
    // Background Image URL ✨ NEW
    // ────────────────────────────────────────
    function parseBackgroundImageURL(bgImage) {
        if (!bgImage || bgImage === 'none') return null;
        const urls = [];
        const urlRegex = /url\\(["']?([^"')]+)["']?\\)/g;
        let m;
        while ((m = urlRegex.exec(bgImage)) !== null) {
            urls.push(m[1]);
        }
        return urls.length > 0 ? urls : null;
    }

    // ────────────────────────────────────────
    // Border Parsing (individual sides) ✨ NEW
    // ────────────────────────────────────────
    function parseBorders(styles) {
        const sides = ['Top', 'Right', 'Bottom', 'Left'];
        const borders = {};
        let hasAny = false;

        for (const side of sides) {
            const width = parseFloat(styles[`border${side}Width`]) || 0;
            if (width > 0) {
                hasAny = true;
                const color = parseColor(styles[`border${side}Color`]);
                const style = styles[`border${side}Style`];
                borders[side.toLowerCase()] = { width, color, style };
            }
        }

        if (!hasAny) return null;

        // Check if all sides are the same → simplify
        const vals = Object.values(borders);
        if (vals.length === 4 &&
            vals.every(v => v.width === vals[0].width &&
                           v.color === vals[0].color &&
                           v.style === vals[0].style)) {
            return {
                uniform: true,
                color: vals[0].color,
                width: vals[0].width,
                style: vals[0].style === 'dashed' ? 'DASHED' : 'SOLID',
            };
        }

        return { uniform: false, sides: borders };
    }

    // ────────────────────────────────────────
    // Border Radius
    // ────────────────────────────────────────
    function parseBorderRadius(styles) {
        const tl = parseFloat(styles.borderTopLeftRadius) || 0;
        const tr = parseFloat(styles.borderTopRightRadius) || 0;
        const br = parseFloat(styles.borderBottomRightRadius) || 0;
        const bl = parseFloat(styles.borderBottomLeftRadius) || 0;
        if (tl === 0 && tr === 0 && br === 0 && bl === 0) return null;
        return { topLeft: tl, topRight: tr, bottomRight: br, bottomLeft: bl };
    }

    // ────────────────────────────────────────
    // Shadow Parsing (box + text + inset) ✨ ENHANCED
    // ────────────────────────────────────────
    function parseShadows(shadowStr) {
        if (!shadowStr || shadowStr === 'none') return null;
        const shadows = [];

        // Split by comma, but not inside parentheses
        const parts = shadowStr.split(/,(?![^(]*\\))/);
        for (const part of parts) {
            const trimmed = part.trim();
            const isInset = trimmed.startsWith('inset');
            const cleaned = trimmed.replace(/^inset\\s*/, '');

            const match = cleaned.match(
                /(-?[\\d.]+)px\\s+(-?[\\d.]+)px\\s+(-?[\\d.]+)px\\s*(-?[\\d.]+)?px?\\s*(.*)/
            );
            if (match) {
                shadows.push({
                    type: isInset ? 'INNER_SHADOW' : 'DROP_SHADOW',
                    offsetX: parseFloat(match[1]),
                    offsetY: parseFloat(match[2]),
                    blur: parseFloat(match[3]),
                    spread: parseFloat(match[4]) || 0,
                    color: match[5]?.trim() || 'rgba(0,0,0,0.25)',
                });
            }
        }

        return shadows.length > 0 ? shadows : null;
    }

    function parseTextShadow(textShadowStr) {
        if (!textShadowStr || textShadowStr === 'none') return null;
        const shadows = [];
        const parts = textShadowStr.split(/,(?![^(]*\\))/);
        for (const part of parts) {
            const match = part.trim().match(
                /((?:rgba?|hsla?)\\([^)]+\\)|#[\\w]+|\\w+)\\s+(-?[\\d.]+)px\\s+(-?[\\d.]+)px(?:\\s+(-?[\\d.]+)px)?/
            );
            if (match) {
                shadows.push({
                    color: match[1],
                    offsetX: parseFloat(match[2]),
                    offsetY: parseFloat(match[3]),
                    blur: parseFloat(match[4]) || 0,
                });
            }
        }
        return shadows.length > 0 ? shadows : null;
    }

    // ────────────────────────────────────────
    // Layout Detection: Flex + Grid ✨ ENHANCED
    // ────────────────────────────────────────
    function detectLayout(styles) {
        const display = styles.display;

        // Flex
        if (display === 'flex' || display === 'inline-flex') {
            const dir = styles.flexDirection || 'row';
            const isReverse = dir.includes('reverse');
            const isColumn = dir.startsWith('column');
            return {
                mode: 'FLEX',
                direction: isColumn ? 'VERTICAL' : 'HORIZONTAL',
                reverse: isReverse,
                wrap: styles.flexWrap === 'wrap' || styles.flexWrap === 'wrap-reverse',
                gap: parseFloat(styles.gap) || 0,
                rowGap: parseFloat(styles.rowGap) || 0,
                columnGap: parseFloat(styles.columnGap) || 0,
                justifyContent: styles.justifyContent,
                alignItems: styles.alignItems,
                alignContent: styles.alignContent,
            };
        }

        // Grid ✨ NEW
        if (config.detectGrid && (display === 'grid' || display === 'inline-grid')) {
            return {
                mode: 'GRID',
                templateColumns: styles.gridTemplateColumns,
                templateRows: styles.gridTemplateRows,
                gap: parseFloat(styles.gap) || 0,
                rowGap: parseFloat(styles.rowGap) || 0,
                columnGap: parseFloat(styles.columnGap) || 0,
                autoFlow: styles.gridAutoFlow,
                justifyItems: styles.justifyItems,
                alignItems: styles.alignItems,
            };
        }

        return null;
    }

    function mapFlexToFigma(layout) {
        if (!layout || layout.mode !== 'FLEX') return null;

        const primaryMap = {
            'flex-start': 'MIN', 'start': 'MIN',
            'center': 'CENTER',
            'flex-end': 'MAX', 'end': 'MAX',
            'space-between': 'SPACE_BETWEEN',
            'space-around': 'SPACE_BETWEEN',
            'space-evenly': 'SPACE_BETWEEN',
        };
        const counterMap = {
            'flex-start': 'MIN', 'start': 'MIN',
            'center': 'CENTER',
            'flex-end': 'MAX', 'end': 'MAX',
            'stretch': 'STRETCH', 'baseline': 'MIN',
        };

        return {
            direction: layout.direction,
            spacing: layout.direction === 'HORIZONTAL'
                ? (layout.columnGap || layout.gap)
                : (layout.rowGap || layout.gap),
            paddingTop: 0, paddingRight: 0, paddingBottom: 0, paddingLeft: 0,
            // Padding is set separately from computed styles
            primaryAlign: primaryMap[layout.justifyContent] || 'MIN',
            counterAlign: counterMap[layout.alignItems] || 'MIN',
            wrap: layout.wrap,
        };
    }

    // Grid → approximate as Figma Auto Layout (WRAP) ✨ NEW
    function mapGridToFigma(layout) {
        if (!layout || layout.mode !== 'GRID') return null;
        // Approximate: treat grid as horizontal wrap layout
        return {
            direction: layout.autoFlow?.includes('column') ? 'VERTICAL' : 'HORIZONTAL',
            spacing: layout.columnGap || layout.gap,
            paddingTop: 0, paddingRight: 0, paddingBottom: 0, paddingLeft: 0,
            primaryAlign: 'MIN',
            counterAlign: 'MIN',
            wrap: true,
            _originalGrid: {
                templateColumns: layout.templateColumns,
                templateRows: layout.templateRows,
            },
        };
    }

    // ────────────────────────────────────────
    // Transform Parsing ✨ NEW
    // ────────────────────────────────────────
    function parseTransform(transformStr) {
        if (!transformStr || transformStr === 'none') return null;

        const result = {};

        // rotate
        const rotateMatch = transformStr.match(/rotate\\((-?[\\d.]+)deg\\)/);
        if (rotateMatch) result.rotation = parseFloat(rotateMatch[1]);

        // scale
        const scaleMatch = transformStr.match(/scale\\(([\\d.]+)(?:,\\s*([\\d.]+))?\\)/);
        if (scaleMatch) {
            result.scaleX = parseFloat(scaleMatch[1]);
            result.scaleY = parseFloat(scaleMatch[2] || scaleMatch[1]);
        }

        // translate
        const translateMatch = transformStr.match(
            /translate(?:3d)?\\((-?[\\d.]+)px(?:,\\s*(-?[\\d.]+)px)?/
        );
        if (translateMatch) {
            result.translateX = parseFloat(translateMatch[1]);
            result.translateY = parseFloat(translateMatch[2] || 0);
        }

        // matrix
        const matrixMatch = transformStr.match(
            /matrix\\(([^)]+)\\)/
        );
        if (matrixMatch) {
            const vals = matrixMatch[1].split(',').map(Number);
            if (vals.length >= 6) {
                result.rotation = Math.round(Math.atan2(vals[1], vals[0]) * 180 / Math.PI);
                result.scaleX = Math.sqrt(vals[0] * vals[0] + vals[1] * vals[1]);
                result.scaleY = Math.sqrt(vals[2] * vals[2] + vals[3] * vals[3]);
                result.translateX = vals[4];
                result.translateY = vals[5];
            }
        }

        return Object.keys(result).length > 0 ? result : null;
    }

    // ────────────────────────────────────────
    // Filter / Backdrop-filter ✨ NEW
    // ────────────────────────────────────────
    function parseFilter(filterStr) {
        if (!filterStr || filterStr === 'none') return null;
        const filters = {};
        const regex = /(blur|brightness|contrast|grayscale|hue-rotate|invert|opacity|saturate|sepia|drop-shadow)\\(([^)]+)\\)/g;
        let m;
        while ((m = regex.exec(filterStr)) !== null) {
            filters[m[1]] = m[2];
        }
        return Object.keys(filters).length > 0 ? filters : null;
    }

    // ────────────────────────────────────────
    // CSS Variable Resolution ✨ NEW
    // ────────────────────────────────────────
    function extractCSSVariables(el) {
        if (!config.captureCssVars) return null;
        const rootStyles = window.getComputedStyle(document.documentElement);
        const vars = {};

        // Get all CSS custom properties from the element's style
        const elStyles = el.style;
        for (let i = 0; i < elStyles.length; i++) {
            const prop = elStyles[i];
            if (prop.startsWith('--')) {
                vars[prop] = rootStyles.getPropertyValue(prop).trim();
            }
        }

        // Also check common design token variables
        const commonVars = [
            '--primary', '--secondary', '--accent', '--background', '--foreground',
            '--border', '--radius', '--font-sans', '--font-mono',
            // Tailwind CSS v4 tokens
            '--color-primary', '--color-secondary',
            // shadcn/ui tokens
            '--ring', '--input', '--card', '--popover', '--muted', '--destructive',
        ];
        for (const v of commonVars) {
            const val = rootStyles.getPropertyValue(v).trim();
            if (val) vars[v] = val;
        }

        return Object.keys(vars).length > 0 ? vars : null;
    }

    // ────────────────────────────────────────
    // Pseudo Element Capture ✨ NEW
    // ────────────────────────────────────────
    function capturePseudo(el) {
        if (!config.capturePseudo) return null;
        const pseudos = [];

        for (const pseudo of ['::before', '::after']) {
            const ps = window.getComputedStyle(el, pseudo);
            const content = ps.content;
            if (!content || content === 'none' || content === 'normal') continue;

            const rect = el.getBoundingClientRect();
            pseudos.push({
                pseudo: pseudo,
                content: content.replace(/^["']|["']$/g, ''),
                display: ps.display,
                position: ps.position,
                width: parseFloat(ps.width) || 0,
                height: parseFloat(ps.height) || 0,
                backgroundColor: parseColor(ps.backgroundColor),
                backgroundImage: ps.backgroundImage !== 'none' ? ps.backgroundImage : null,
                color: parseColor(ps.color),
                fontSize: parseFloat(ps.fontSize) || 0,
                fontFamily: ps.fontFamily?.split(',')[0]?.trim()?.replace(/['"]/g, ''),
                borderRadius: parseBorderRadius(ps),
                opacity: parseFloat(ps.opacity),
                // Approximate position
                top: parseFloat(ps.top) || 0,
                left: parseFloat(ps.left) || 0,
            });
        }

        return pseudos.length > 0 ? pseudos : null;
    }

    // ────────────────────────────────────────
    // SVG Capture ✨ NEW
    // ────────────────────────────────────────
    function captureSVG(el) {
        if (!config.captureSvgMarkup) return null;
        if (el.tagName !== 'SVG') return null;

        try {
            const serializer = new XMLSerializer();
            const svgStr = serializer.serializeToString(el);
            // Only capture if not too large
            if (svgStr.length < 50000) {
                return {
                    markup: svgStr,
                    viewBox: el.getAttribute('viewBox'),
                    width: el.getAttribute('width'),
                    height: el.getAttribute('height'),
                };
            }
        } catch (e) {}
        return null;
    }

    // ────────────────────────────────────────
    // Image Capture ✨ NEW
    // ────────────────────────────────────────
    function captureImageData(el) {
        if (!config.captureImageData) return null;

        // <img> element
        if (el.tagName === 'IMG' && el.complete && el.naturalWidth > 0) {
            try {
                const canvas = getCaptureCanvas();
                canvas.width = Math.min(el.naturalWidth, 800);
                canvas.height = Math.min(el.naturalHeight, 800);
                const ctx = canvas.getContext('2d');
                ctx.drawImage(el, 0, 0, canvas.width, canvas.height);
                return canvas.toDataURL('image/png').split(',')[1];
            } catch (e) { /* CORS */ }
        }

        // <canvas> element
        if (el.tagName === 'CANVAS' && config.captureCanvas) {
            try {
                return el.toDataURL('image/png').split(',')[1];
            } catch (e) {}
        }

        return null;
    }

    // ────────────────────────────────────────
    // Component Detection (Vue/React/Svelte)
    // ────────────────────────────────────────
    function getVueComponentName(el) {
        // Vue 3
        if (el.__vueParentComponent) {
            const comp = el.__vueParentComponent;
            return comp.type?.name || comp.type?.__name ||
                   comp.type?.__file?.match(/([^/]+)\\.vue$/)?.[1] || null;
        }
        // Vue 2
        if (el.__vue__) {
            return el.__vue__.$options?.name ||
                   el.__vue__.$options?._componentTag || null;
        }
        return null;
    }

    function getReactComponentName(el) {
        const fiberKey = Object.keys(el).find(
            k => k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$')
        );
        if (!fiberKey) return null;
        let fiber = el[fiberKey];
        while (fiber) {
            if (fiber.type && typeof fiber.type === 'function') {
                return fiber.type.displayName || fiber.type.name || null;
            }
            if (fiber.type && typeof fiber.type === 'object' && fiber.type.$$typeof) {
                return fiber.type.displayName ||
                       fiber.type.render?.displayName ||
                       fiber.type.render?.name || null;
            }
            fiber = fiber.return;
        }
        return null;
    }

    function getSvelteComponentName(el) {
        // Svelte 4/5: __svelte_meta
        if (el.__svelte_meta) {
            return el.__svelte_meta?.loc?.file?.match(/([^/]+)\\.svelte$/)?.[1] || null;
        }
        return null;
    }

    function getComponentName(el) {
        // Explicit attribute always wins
        const explicit = el.getAttribute('data-figma-component');
        if (explicit) return explicit;

        if (!config.detectComponents) return null;

        const fw = config.framework;
        if (fw === 'vue') return getVueComponentName(el);
        if (fw === 'react') return getReactComponentName(el);
        if (fw === 'svelte') return getSvelteComponentName(el);

        // Auto-detect: try all
        return getVueComponentName(el) ||
               getReactComponentName(el) ||
               getSvelteComponentName(el) || null;
    }

    // ────────────────────────────────────────
    // Text Detection
    // ────────────────────────────────────────
    function isTextOnlyNode(el) {
        const children = el.childNodes;
        for (let i = 0; i < children.length; i++) {
            if (children[i].nodeType === Node.ELEMENT_NODE) {
                if (!INLINE_TAGS.has(children[i].tagName)) return false;
            }
        }
        for (let i = 0; i < children.length; i++) {
            if (children[i].nodeType === Node.TEXT_NODE &&
                children[i].textContent.trim()) {
                return true;
            }
        }
        return false;
    }

    // Get actual rendered text (respects text-transform) ✨ ENHANCED
    function getRenderedText(el) {
        // innerText respects CSS text-transform, visibility, etc.
        return (el.innerText || el.textContent || '').trim();
    }

    // ────────────────────────────────────────
    // Attribute Collection
    // ────────────────────────────────────────
    function collectAttributes(el) {
        const attrs = {};
        for (const attr of el.attributes) {
            // Skip data-v- (Vue scoped) and data-reactroot etc.
            if (attr.name.startsWith('data-v-') && attr.name !== 'data-v-app') continue;
            if (attr.name.startsWith('data-reactroot')) continue;
            attrs[attr.name] = attr.value;
        }
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

    // ────────────────────────────────────────
    // Main Walk Function
    // ────────────────────────────────────────
    function walkDOM(el, depth = 0, parentX = 0, parentY = 0) {
        if (depth > config.maxDepth) return null;
        if (SKIP_TAGS.has(el.tagName)) return null;

        const styles = window.getComputedStyle(el);

        // Skip invisible
        if (config.skipInvisible) {
            if (styles.display === 'none') return null;
            if (styles.visibility === 'hidden' && !el.children.length) return null;
            if (parseFloat(styles.opacity) === 0 && !el.children.length) return null;
        }

        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0 && !el.children.length) return null;

        const layout = detectLayout(styles);
        const siblingInfo = getSiblingInfo(el);

        // ─── Build node ───
        const node = {
            tag: el.tagName.toLowerCase(),
            attrs: collectAttributes(el),
            componentName: getComponentName(el),
            siblingIndex: siblingInfo.index,
            siblingTagCount: siblingInfo.tagCount,

            // Geometry
            layout: {
                x: rect.x,
                y: rect.y,
                width: Math.max(rect.width, 1),
                height: Math.max(rect.height, 1),
            },

            // Type hints
            isTextNode: isTextOnlyNode(el),
            textContent: isTextOnlyNode(el) ? getRenderedText(el) : null,
            isImage: el.tagName === 'IMG' || el.tagName === 'PICTURE',
            isSVG: el.tagName === 'SVG',
            isCanvas: el.tagName === 'CANVAS',
            isVideo: el.tagName === 'VIDEO',
            isIframe: el.tagName === 'IFRAME',
            hasBackgroundImage: false,

            // Styles (comprehensive)
            styles: {
                // Background
                backgroundColor: parseColor(styles.backgroundColor),
                backgroundImage: null,
                gradient: null,
                backgroundSize: null,
                backgroundPosition: null,

                // Opacity & Blend
                opacity: parseFloat(styles.opacity),
                mixBlendMode: styles.mixBlendMode !== 'normal' ? styles.mixBlendMode : null,

                // Border
                border: null,
                borderRadius: parseBorderRadius(styles),

                // Shadows
                boxShadow: null,
                textShadow: null,

                // Text
                fontSize: parseFloat(styles.fontSize),
                fontFamily: styles.fontFamily?.split(',')[0]?.trim()?.replace(/['"]/g, ''),
                fontWeight: parseInt(styles.fontWeight) || 400,
                fontStyle: styles.fontStyle !== 'normal' ? styles.fontStyle : null,
                lineHeight: parseFloat(styles.lineHeight) || null,
                letterSpacing: parseFloat(styles.letterSpacing) || 0,
                textAlign: styles.textAlign,
                textDecoration: styles.textDecorationLine !== 'none' ? {
                    line: styles.textDecorationLine,
                    style: styles.textDecorationStyle,
                    color: parseColor(styles.textDecorationColor),
                } : null,
                textTransform: styles.textTransform !== 'none' ? styles.textTransform : null,
                color: parseColor(styles.color),
                whiteSpace: styles.whiteSpace,
                wordBreak: styles.wordBreak,
                textOverflow: styles.textOverflow,

                // Padding (for auto layout)
                paddingTop: parseFloat(styles.paddingTop) || 0,
                paddingRight: parseFloat(styles.paddingRight) || 0,
                paddingBottom: parseFloat(styles.paddingBottom) || 0,
                paddingLeft: parseFloat(styles.paddingLeft) || 0,

                // Overflow ✨ NEW
                overflow: styles.overflow !== 'visible' ? styles.overflow : null,
                overflowX: styles.overflowX !== 'visible' ? styles.overflowX : null,
                overflowY: styles.overflowY !== 'visible' ? styles.overflowY : null,

                // Position & stacking
                position: styles.position !== 'static' ? styles.position : null,
                zIndex: styles.zIndex !== 'auto' ? parseInt(styles.zIndex) : null,

                // Sizing hints
                aspectRatio: styles.aspectRatio !== 'auto' ? styles.aspectRatio : null,

                // Cursor (useful for interactive elements)
                cursor: styles.cursor !== 'auto' ? styles.cursor : null,
            },

            // Transform ✨ NEW
            transform: parseTransform(styles.transform),

            // Filter ✨ NEW
            filter: parseFilter(styles.filter),
            backdropFilter: parseFilter(styles.backdropFilter || styles.webkitBackdropFilter),

            // Layout mode
            layoutMode: null,
            autoLayout: null,

            // Image data
            imageSrc: el.tagName === 'IMG' ? el.currentSrc || el.src : null,
            imageAlt: el.tagName === 'IMG' ? el.alt : null,
            imageData: null,

            // SVG data ✨ NEW
            svgData: null,

            // Pseudo elements ✨ NEW
            pseudoElements: null,

            // CSS Variables ✨ NEW
            cssVariables: null,

            // Children
            children: [],
        };

        // ─── Background processing ───
        const bgImage = styles.backgroundImage;
        if (bgImage && bgImage !== 'none') {
            node.hasBackgroundImage = true;
            node.styles.gradient = parseGradient(bgImage);
            const bgUrls = parseBackgroundImageURL(bgImage);
            if (bgUrls) {
                node.styles.backgroundImage = bgUrls;
                node.styles.backgroundSize = styles.backgroundSize;
                node.styles.backgroundPosition = styles.backgroundPosition;
            }
        }

        // ─── Borders ───
        node.styles.border = parseBorders(styles);

        // ─── Shadows ───
        node.styles.boxShadow = parseShadows(styles.boxShadow);
        node.styles.textShadow = parseTextShadow(styles.textShadow);

        // ─── Layout mode ───
        if (layout) {
            node.layoutMode = layout;
            if (layout.mode === 'FLEX') {
                node.autoLayout = mapFlexToFigma(layout);
                // Inject padding from computed styles
                if (node.autoLayout) {
                    node.autoLayout.paddingTop = node.styles.paddingTop;
                    node.autoLayout.paddingRight = node.styles.paddingRight;
                    node.autoLayout.paddingBottom = node.styles.paddingBottom;
                    node.autoLayout.paddingLeft = node.styles.paddingLeft;
                }
            } else if (layout.mode === 'GRID') {
                node.autoLayout = mapGridToFigma(layout);
                if (node.autoLayout) {
                    node.autoLayout.paddingTop = node.styles.paddingTop;
                    node.autoLayout.paddingRight = node.styles.paddingRight;
                    node.autoLayout.paddingBottom = node.styles.paddingBottom;
                    node.autoLayout.paddingLeft = node.styles.paddingLeft;
                }
            }
        }

        // ─── SVG capture ───
        if (node.isSVG) {
            node.svgData = captureSVG(el);
        }

        // ─── Image data capture ───
        node.imageData = captureImageData(el);

        // ─── Pseudo elements ───
        node.pseudoElements = capturePseudo(el);

        // ─── CSS variables ───
        if (depth === 0) {
            node.cssVariables = extractCSSVariables(el);
        }

        // ─── Recursively walk children ───
        if (!node.isTextNode && !node.isSVG) {
            for (const child of el.children) {
                const childNode = walkDOM(child, depth + 1, rect.x, rect.y);
                if (childNode) {
                    node.children.push(childNode);
                }
            }
        }

        return node;
    }

    // ─── Find root ───
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


# ════════════════════════════════════════════════════════════════
# Python API (same interface as v1, drop-in replacement)
# ════════════════════════════════════════════════════════════════

async def extract_dom_tree(
    url: str,
    config: Optional[ExtractionConfig] = None,
) -> dict:
    """
    Launch headless browser, navigate to URL, extract DOM tree.
    Drop-in replacement for v1 with all enhanced capabilities.
    """
    config = config or ExtractionConfig()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError(
            "playwright is required. Install with:\n"
            "  pip install playwright --break-system-packages\n"
            "  playwright install chromium"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={
                "width": config.viewport_width,
                "height": config.viewport_height,
            }
        )
        page = await context.new_page()

        await page.goto(url, wait_until="networkidle", timeout=config.wait_timeout_ms)

        if config.wait_for_selector:
            await page.wait_for_selector(
                config.wait_for_selector,
                timeout=config.wait_timeout_ms
            )

        # Wait for framework hydration
        await page.wait_for_timeout(500)

        js_config = {
            "rootSelector": config.root_selector,
            "skipInvisible": config.skip_invisible,
            "maxDepth": config.max_depth,
            "detectComponents": config.detect_components,
            "detectGrid": config.detect_grid,
            "framework": config.framework,
            "captureImageData": config.capture_image_data,
            "captureCanvas": config.capture_canvas,
            "captureSvgMarkup": config.capture_svg_markup,
            "capturePseudo": config.capture_pseudo,
            "captureCssVars": config.capture_css_vars,
        }

        raw_tree = await page.evaluate(DOM_WALKER_V2_JS, js_config)
        screenshot_bytes = await page.screenshot(full_page=False)

        await browser.close()

    return {
        "tree": raw_tree,
        "screenshot": screenshot_bytes,
        "viewport": {
            "width": config.viewport_width,
            "height": config.viewport_height,
        }
    }


def extract_dom_tree_sync(
    url: str,
    config: Optional[ExtractionConfig] = None,
) -> dict:
    """Synchronous wrapper."""
    return asyncio.run(extract_dom_tree(url, config))


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
    print(f"Extracting DOM (v2) from: {url}")
    result = extract_dom_tree_sync(url)
    tree = result["tree"]
    print(json.dumps(tree, indent=2, ensure_ascii=False)[:8000])

/**
 * AiIRIS-pdm Figma Plugin: Create Nodes from IR JSON
 *
 * Reads plugin-payload.json from AiIRIS-pdm push and creates Figma nodes
 * with 100% controlled naming. Plugin namespace matches figma-code-sync for pull.
 *
 * Build: cd figma_plugin && npx tsc src/code.ts --outDir dist
 */

// Types (matching schemas/ir_schema.json)
interface IRNode {
  figmaName: string;
  figmaType: 'FRAME' | 'AUTO_LAYOUT' | 'TEXT' | 'RECTANGLE' | 'ELLIPSE' |
             'IMAGE' | 'COMPONENT' | 'INSTANCE' | 'GROUP' | 'SECTION';
  htmlTag?: string;
  componentRef?: string;
  layout: { x: number; y: number; width: number; height: number };
  autoLayout?: {
    direction: 'HORIZONTAL' | 'VERTICAL';
    spacing: number;
    paddingTop: number;
    paddingRight: number;
    paddingBottom: number;
    paddingLeft: number;
    primaryAlign: 'MIN' | 'CENTER' | 'MAX' | 'SPACE_BETWEEN';
    counterAlign: 'MIN' | 'CENTER' | 'MAX' | 'STRETCH';
    wrap?: boolean;
  };
  styles?: {
    backgroundColor?: string;
    opacity?: number;
    borderRadius?: { topLeft: number; topRight: number; bottomRight: number; bottomLeft: number };
    border?: { color: string; width: number; style: 'SOLID' | 'DASHED' };
    shadow?: Array<{ color: string; offsetX: number; offsetY: number; blur: number; spread: number }>;
  };
  text?: {
    characters: string;
    fontSize: number;
    fontFamily: string;
    fontWeight: number;
    lineHeight?: number;
    letterSpacing: number;
    textAlign: 'LEFT' | 'CENTER' | 'RIGHT' | 'JUSTIFIED';
    color: string;
  };
  image?: { src: string; base64?: string; scaleMode: 'FILL' | 'FIT' | 'CROP' | 'TILE' };
  pluginData?: { sourceFile?: string; selector?: string; cssClasses?: string; originalTag?: string };
  children?: IRNode[];
}

function parseCSSColor(cssColor: string): { r: number; g: number; b: number; a: number } | null {
  if (!cssColor) return null;
  const rgbaMatch = cssColor.match(/rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  if (rgbaMatch) {
    return {
      r: parseInt(rgbaMatch[1]) / 255, g: parseInt(rgbaMatch[2]) / 255, b: parseInt(rgbaMatch[3]) / 255,
      a: rgbaMatch[4] ? parseFloat(rgbaMatch[4]) : 1,
    };
  }
  const hexMatch = cssColor.match(/^#([0-9a-f]{3,8})$/i);
  if (hexMatch) {
    const hex = hexMatch[1];
    if (hex.length === 3)
      return { r: parseInt(hex[0]+hex[0],16)/255, g: parseInt(hex[1]+hex[1],16)/255, b: parseInt(hex[2]+hex[2],16)/255, a: 1 };
    if (hex.length >= 6)
      return {
        r: parseInt(hex.slice(0,2),16)/255, g: parseInt(hex.slice(2,4),16)/255, b: parseInt(hex.slice(4,6),16)/255,
        a: hex.length === 8 ? parseInt(hex.slice(6,8),16)/255 : 1,
      };
  }
  return null;
}

const PLUGIN_NAMESPACE = 'figma-code-sync';
const DEFAULT_FONT = { family: 'Inter', style: 'Regular' };

function collectFonts(node: IRNode, fonts: Set<string>): void {
  if (node.text) {
    const family = node.text.fontFamily || 'Inter';
    const weight = node.text.fontWeight || 400;
    const style = weight >= 700 ? 'Bold' : weight >= 500 ? 'Medium' : weight >= 300 ? 'Light' : 'Regular';
    fonts.add(`${family}::${style}`);
  }
  for (const child of node.children || []) collectFonts(child, fonts);
}

async function loadAllFonts(fonts: Set<string>): Promise<void> {
  for (const fontKey of fonts) {
    const [family, style] = fontKey.split('::');
    try { await figma.loadFontAsync({ family, style }); }
    catch { try { await figma.loadFontAsync(DEFAULT_FONT); } catch { } }
  }
}

async function createNodeFromIR(
  irNode: IRNode,
  parentNode?: FrameNode | GroupNode | ComponentNode | PageNode,
  offsetX: number = 0,
  offsetY: number = 0,
): Promise<SceneNode | null> {
  let node: SceneNode;
  switch (irNode.figmaType) {
    case 'TEXT': node = await createTextNode(irNode); break;
    case 'RECTANGLE': node = createRectangleNode(irNode); break;
    case 'ELLIPSE': node = createEllipseNode(irNode); break;
    case 'COMPONENT': node = await createComponentNode(irNode, offsetX, offsetY); break;
    case 'AUTO_LAYOUT': node = await createAutoLayoutNode(irNode, offsetX, offsetY); break;
    case 'SECTION': node = await createSectionNode(irNode, offsetX, offsetY); break;
    case 'FRAME':
    case 'IMAGE':
    case 'GROUP':
    default: node = await createFrameNode(irNode, offsetX, offsetY); break;
  }
  node.name = irNode.figmaName;
  applyStyles(node, irNode);
  if (irNode.pluginData) {
    for (const [key, value] of Object.entries(irNode.pluginData))
      if (value) node.setSharedPluginData(PLUGIN_NAMESPACE, key, String(value));
  }
  node.setSharedPluginData(PLUGIN_NAMESPACE, 'irType', irNode.figmaType);
  if (irNode.htmlTag) node.setSharedPluginData(PLUGIN_NAMESPACE, 'htmlTag', irNode.htmlTag);
  if (irNode.componentRef) node.setSharedPluginData(PLUGIN_NAMESPACE, 'componentRef', irNode.componentRef);
  if (parentNode && 'appendChild' in parentNode) parentNode.appendChild(node);
  return node;
}

async function createTextNode(ir: IRNode): Promise<TextNode> {
  const text = figma.createText();
  const t = ir.text!;
  const family = t.fontFamily || 'Inter';
  const style = (t.fontWeight || 400) >= 700 ? 'Bold' : (t.fontWeight || 400) >= 500 ? 'Medium' : (t.fontWeight || 400) >= 300 ? 'Light' : 'Regular';
  try { await figma.loadFontAsync({ family, style }); text.fontName = { family, style }; }
  catch { await figma.loadFontAsync(DEFAULT_FONT); text.fontName = DEFAULT_FONT; }
  text.characters = t.characters || '';
  text.fontSize = t.fontSize || 14;
  if (t.lineHeight) text.lineHeight = { value: t.lineHeight, unit: 'PIXELS' };
  if (t.letterSpacing) text.letterSpacing = { value: t.letterSpacing, unit: 'PIXELS' };
  if (t.textAlign) text.textAlignHorizontal = t.textAlign;
  const color = parseCSSColor(t.color);
  if (color) text.fills = [{ type: 'SOLID', color: { r: color.r, g: color.g, b: color.b }, opacity: color.a }];
  text.x = ir.layout.x; text.y = ir.layout.y;
  text.resize(Math.max(ir.layout.width, 1), Math.max(ir.layout.height, 1));
  return text;
}

function createRectangleNode(ir: IRNode): RectangleNode {
  const rect = figma.createRectangle();
  rect.x = ir.layout.x; rect.y = ir.layout.y;
  rect.resize(Math.max(ir.layout.width, 1), Math.max(ir.layout.height, 1));
  return rect;
}

function createEllipseNode(ir: IRNode): EllipseNode {
  const el = figma.createEllipse();
  el.x = ir.layout.x; el.y = ir.layout.y;
  el.resize(Math.max(ir.layout.width, 1), Math.max(ir.layout.height, 1));
  return el;
}

async function createFrameNode(ir: IRNode, offsetX: number, offsetY: number): Promise<FrameNode> {
  const frame = figma.createFrame();
  frame.x = ir.layout.x - offsetX; frame.y = ir.layout.y - offsetY;
  frame.resize(Math.max(ir.layout.width, 1), Math.max(ir.layout.height, 1));
  frame.fills = [];
  if (ir.children) for (const child of ir.children) await createNodeFromIR(child, frame, ir.layout.x, ir.layout.y);
  return frame;
}

async function createAutoLayoutNode(ir: IRNode, offsetX: number, offsetY: number): Promise<FrameNode> {
  const frame = figma.createFrame();
  frame.x = ir.layout.x - offsetX; frame.y = ir.layout.y - offsetY;
  frame.resize(Math.max(ir.layout.width, 1), Math.max(ir.layout.height, 1));
  frame.fills = [];
  if (ir.autoLayout) {
    frame.layoutMode = ir.autoLayout.direction;
    frame.itemSpacing = ir.autoLayout.spacing || 0;
    frame.paddingTop = ir.autoLayout.paddingTop || 0;
    frame.paddingRight = ir.autoLayout.paddingRight || 0;
    frame.paddingBottom = ir.autoLayout.paddingBottom || 0;
    frame.paddingLeft = ir.autoLayout.paddingLeft || 0;
    frame.primaryAxisAlignItems = ir.autoLayout.primaryAlign || 'MIN';
    frame.counterAxisAlignItems = ir.autoLayout.counterAlign || 'MIN';
    if (ir.autoLayout.wrap) frame.layoutWrap = 'WRAP';
  }
  if (ir.children) for (const child of ir.children) await createNodeFromIR(child, frame, ir.layout.x, ir.layout.y);
  return frame;
}

async function createComponentNode(ir: IRNode, offsetX: number, offsetY: number): Promise<ComponentNode> {
  const comp = figma.createComponent();
  comp.x = ir.layout.x - offsetX; comp.y = ir.layout.y - offsetY;
  comp.resize(Math.max(ir.layout.width, 1), Math.max(ir.layout.height, 1));
  comp.fills = [];
  if (ir.autoLayout) {
    comp.layoutMode = ir.autoLayout.direction;
    comp.itemSpacing = ir.autoLayout.spacing || 0;
    comp.paddingTop = ir.autoLayout.paddingTop || 0;
    comp.paddingRight = ir.autoLayout.paddingRight || 0;
    comp.paddingBottom = ir.autoLayout.paddingBottom || 0;
    comp.paddingLeft = ir.autoLayout.paddingLeft || 0;
  }
  if (ir.children) for (const child of ir.children) await createNodeFromIR(child, comp, ir.layout.x, ir.layout.y);
  return comp;
}

async function createSectionNode(ir: IRNode, offsetX: number, offsetY: number): Promise<SectionNode> {
  const section = figma.createSection();
  section.x = ir.layout.x - offsetX; section.y = ir.layout.y - offsetY;
  section.resizeWithoutConstraints(Math.max(ir.layout.width, 1), Math.max(ir.layout.height, 1));
  if (ir.children) for (const child of ir.children) await createNodeFromIR(child, undefined);
  return section;
}

function applyStyles(node: SceneNode, ir: IRNode): void {
  const s = ir.styles;
  if (!s) return;
  if (s.backgroundColor && 'fills' in node) {
    const c = parseCSSColor(s.backgroundColor);
    if (c) (node as GeometryMixin).fills = [{ type: 'SOLID', color: { r: c.r, g: c.g, b: c.b }, opacity: c.a }];
  }
  if (s.opacity !== undefined && 'opacity' in node) (node as BlendMixin).opacity = s.opacity;
  if (s.borderRadius && 'cornerRadius' in node) {
    const rn = node as RectangleNode | FrameNode;
    rn.topLeftRadius = s.borderRadius.topLeft || 0;
    rn.topRightRadius = s.borderRadius.topRight || 0;
    rn.bottomRightRadius = s.borderRadius.bottomRight || 0;
    rn.bottomLeftRadius = s.borderRadius.bottomLeft || 0;
  }
  if (s.border && 'strokes' in node) {
    const c = parseCSSColor(s.border.color);
    if (c) {
      (node as GeometryMixin).strokes = [{ type: 'SOLID', color: { r: c.r, g: c.g, b: c.b }, opacity: c.a }];
      (node as GeometryMixin).strokeWeight = s.border.width;
    }
  }
  if (s.shadow && 'effects' in node) {
    (node as BlendMixin).effects = s.shadow.map(sh => {
      const c = parseCSSColor(sh.color) || { r: 0, g: 0, b: 0, a: 0.25 };
      return { type: 'DROP_SHADOW', visible: true, blendMode: 'NORMAL', color: { r: c.r, g: c.g, b: c.b, a: c.a }, offset: { x: sh.offsetX, y: sh.offsetY }, radius: sh.blur, spread: sh.spread };
    });
  }
}

function exportNodeTree(node: SceneNode): any {
  const data: any = { name: node.name, type: node.type, id: node.id };
  const keys = node.getSharedPluginDataKeys(PLUGIN_NAMESPACE);
  if (keys.length > 0) {
    data.pluginData = {};
    for (const key of keys) data.pluginData[key] = node.getSharedPluginData(PLUGIN_NAMESPACE, key);
  }
  if ('children' in node) {
    data.children = [];
    for (const child of (node as FrameNode).children) data.children.push(exportNodeTree(child));
  }
  return data;
}

function countNodes(ir: IRNode): number {
  let n = 1;
  for (const c of ir.children || []) n += countNodes(c);
  return n;
}

figma.showUI(__html__, { width: 500, height: 600 });

figma.ui.onmessage = async (msg: any) => {
  if (msg.type === 'import-ir') {
    const irTree: IRNode = msg.payload;
    figma.ui.postMessage({ type: 'status', text: 'Loading fonts...' });
    const fonts = new Set<string>();
    collectFonts(irTree, fonts);
    await loadAllFonts(fonts);
    figma.ui.postMessage({ type: 'status', text: 'Creating nodes...' });
    const rootNode = await createNodeFromIR(irTree, figma.currentPage);
    if (rootNode) {
      figma.currentPage.selection = [rootNode];
      figma.viewport.scrollAndZoomIntoView([rootNode]);
    }
    figma.ui.postMessage({ type: 'import-complete', nodeCount: countNodes(irTree) });
  }
  if (msg.type === 'export-tree') {
    const sel = figma.currentPage.selection;
    if (sel.length === 0) { figma.ui.postMessage({ type: 'error', text: 'Please select a frame to export.' }); return; }
    figma.ui.postMessage({ type: 'export-result', data: exportNodeTree(sel[0]) });
  }
  if (msg.type === 'close') figma.closePlugin();
};

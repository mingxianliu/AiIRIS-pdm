/**
 * Figma plugin environment declarations（含 v2 完整保真型別）
 */
declare const figma: any;
declare const __html__: string;

interface RGB { r: number; g: number; b: number; }
interface RGBA extends RGB { a: number; }

interface ColorStop { position: number; color: RGBA; }
interface GradientPaint {
  type: 'GRADIENT_LINEAR' | 'GRADIENT_RADIAL' | 'GRADIENT_ANGULAR';
  gradientStops: ColorStop[];
  gradientTransform: number[][];
}
interface SolidPaint { type: 'SOLID'; color: RGB; opacity?: number; }
type Paint = SolidPaint | GradientPaint | { type: string; [k: string]: any };

interface Effect {
  type: 'DROP_SHADOW' | 'INNER_SHADOW' | 'LAYER_BLUR' | 'BACKGROUND_BLUR';
  visible?: boolean; blendMode?: string; color?: RGBA;
  offset?: { x: number; y: number }; radius?: number; spread?: number;
}
type BlendMode = string;

interface FontName { family: string; style: string; }

type SceneNode = any;
type FrameNode = any;
type GroupNode = any;
type ComponentNode = any;
type PageNode = any;
type TextNode = any;
type RectangleNode = any;
type EllipseNode = any;
type SectionNode = any;
type GeometryMixin = any;
type BlendMixin = any;

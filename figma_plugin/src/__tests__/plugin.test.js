/**
 * Figma Plugin 純函數單元測試（P2 #11 Figma Plugin）
 *
 * Figma Plugin 的核心邏輯（parseCSSColor、buildGradientPaint、
 * buildFills、buildEffects、countNodes）都是純函數，
 * 可以在 Node.js 環境中直接測試，不需要真實 Figma API。
 *
 * 架構：從 code.ts 抽出可測試的純函數並在此驗證。
 */

// ═══════════════════════════════════════════════════════════════
// 複製 code.ts 的純函數以供測試（與實作保持同步）
// ═══════════════════════════════════════════════════════════════

const NAMED_COLORS = {
  white: "#ffffff",
  black: "#000000",
  red: "#ff0000",
  blue: "#0000ff",
  green: "#008000",
  yellow: "#ffff00",
  transparent: "#00000000",
};

function parseCSSColor(cssColor) {
  if (!cssColor) return null;
  if (NAMED_COLORS[cssColor.toLowerCase()]) {
    return parseCSSColor(NAMED_COLORS[cssColor.toLowerCase()]);
  }
  const rgbaMatch = cssColor.match(
    /rgba?\(\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/
  );
  if (rgbaMatch) {
    return {
      r: parseInt(rgbaMatch[1]) / 255,
      g: parseInt(rgbaMatch[2]) / 255,
      b: parseInt(rgbaMatch[3]) / 255,
      a: rgbaMatch[4] !== undefined ? parseFloat(rgbaMatch[4]) : 1,
    };
  }
  const hexMatch = cssColor.match(/^#([0-9a-f]{3,8})$/i);
  if (hexMatch) {
    const hex = hexMatch[1];
    if (hex.length === 3) {
      return {
        r: parseInt(hex[0] + hex[0], 16) / 255,
        g: parseInt(hex[1] + hex[1], 16) / 255,
        b: parseInt(hex[2] + hex[2], 16) / 255,
        a: 1,
      };
    }
    if (hex.length >= 6) {
      return {
        r: parseInt(hex.substring(0, 2), 16) / 255,
        g: parseInt(hex.substring(2, 4), 16) / 255,
        b: parseInt(hex.substring(4, 6), 16) / 255,
        a:
          hex.length === 8
            ? parseInt(hex.substring(6, 8), 16) / 255
            : 1,
      };
    }
  }
  const hslMatch = cssColor.match(
    /hsla?\(\s*([\d.]+),\s*([\d.]+)%,\s*([\d.]+)%(?:,\s*([\d.]+))?\)/
  );
  if (hslMatch) {
    const h = parseFloat(hslMatch[1]) / 360;
    const s = parseFloat(hslMatch[2]) / 100;
    const l = parseFloat(hslMatch[3]) / 100;
    const a = hslMatch[4] !== undefined ? parseFloat(hslMatch[4]) : 1;
    const { r, g, b } = hslToRgb(h, s, l);
    return { r, g, b, a };
  }
  return null;
}

function hslToRgb(h, s, l) {
  let r, g, b;
  if (s === 0) {
    r = g = b = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }
  return { r, g, b };
}

function hue2rgb(p, q, t) {
  if (t < 0) t += 1;
  if (t > 1) t -= 1;
  if (t < 1 / 6) return p + (q - p) * 6 * t;
  if (t < 1 / 2) return q;
  if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
  return p;
}

function buildGradientPaint(fill) {
  if (!fill.stops || fill.stops.length < 2) return null;
  const gradientStops = fill.stops.map((stop) => {
    const color = parseCSSColor(stop.color) || { r: 0, g: 0, b: 0, a: 1 };
    return { position: stop.position, color };
  });
  if (fill.type === "GRADIENT_LINEAR") {
    const angle = ((fill.angle || 180) * Math.PI) / 180;
    const cos = Math.cos(angle - Math.PI / 2);
    const sin = Math.sin(angle - Math.PI / 2);
    return {
      type: "GRADIENT_LINEAR",
      gradientStops,
      gradientTransform: [
        [cos, sin, 0.5 - cos * 0.5 - sin * 0.5],
        [-sin, cos, 0.5 + sin * 0.5 - cos * 0.5],
      ],
    };
  }
  if (fill.type === "GRADIENT_RADIAL") {
    return {
      type: "GRADIENT_RADIAL",
      gradientStops,
      gradientTransform: [[1, 0, 0], [0, 1, 0]],
    };
  }
  if (fill.type === "GRADIENT_ANGULAR") {
    return {
      type: "GRADIENT_ANGULAR",
      gradientStops,
      gradientTransform: [[1, 0, 0], [0, 1, 0]],
    };
  }
  return null;
}

function buildFills(irFills) {
  const paints = [];
  for (const fill of irFills) {
    if (fill.type === "SOLID") {
      const color = parseCSSColor(fill.color || "");
      if (color) {
        paints.push({
          type: "SOLID",
          color: { r: color.r, g: color.g, b: color.b },
          opacity: color.a,
        });
      }
    } else if (
      fill.type === "GRADIENT_LINEAR" ||
      fill.type === "GRADIENT_RADIAL" ||
      fill.type === "GRADIENT_ANGULAR"
    ) {
      const gp = buildGradientPaint(fill);
      if (gp) paints.push(gp);
    }
  }
  return paints;
}

function buildEffects(irEffects) {
  const effects = [];
  for (const e of irEffects) {
    if (e.type === "DROP_SHADOW" || e.type === "INNER_SHADOW") {
      const color = parseCSSColor(e.color || "rgba(0,0,0,0.25)") || {
        r: 0,
        g: 0,
        b: 0,
        a: 0.25,
      };
      effects.push({
        type: e.type,
        visible: true,
        blendMode: "NORMAL",
        color,
        offset: { x: e.offsetX || 0, y: e.offsetY || 0 },
        radius: e.blur || 0,
        spread: e.spread || 0,
      });
    } else if (e.type === "LAYER_BLUR" || e.type === "BACKGROUND_BLUR") {
      effects.push({ type: e.type, visible: true, radius: e.blur || 0 });
    }
  }
  return effects;
}

function countNodes(ir) {
  let count = 1;
  for (const child of ir.children || []) {
    count += countNodes(child);
  }
  return count;
}

// ═══════════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════════

describe("parseCSSColor", () => {
  test("rgba 格式", () => {
    const c = parseCSSColor("rgba(255, 128, 0, 0.5)");
    expect(c.r).toBeCloseTo(1.0);
    expect(c.g).toBeCloseTo(0.502, 2);
    expect(c.b).toBe(0);
    expect(c.a).toBe(0.5);
  });

  test("rgb 格式（不含 alpha）預設 a=1", () => {
    const c = parseCSSColor("rgb(0, 0, 255)");
    expect(c.r).toBe(0);
    expect(c.b).toBeCloseTo(1.0);
    expect(c.a).toBe(1);
  });

  test("hex 6 碼", () => {
    const c = parseCSSColor("#ff0000");
    expect(c.r).toBeCloseTo(1.0);
    expect(c.g).toBe(0);
    expect(c.b).toBe(0);
    expect(c.a).toBe(1);
  });

  test("hex 3 碼展開", () => {
    const c = parseCSSColor("#fff");
    expect(c.r).toBeCloseTo(1.0);
    expect(c.g).toBeCloseTo(1.0);
    expect(c.b).toBeCloseTo(1.0);
  });

  test("hex 8 碼含 alpha", () => {
    const c = parseCSSColor("#ff000080");
    expect(c.r).toBeCloseTo(1.0);
    expect(c.a).toBeCloseTo(0.502, 2);
  });

  test("named color: white", () => {
    const c = parseCSSColor("white");
    expect(c.r).toBeCloseTo(1.0);
    expect(c.g).toBeCloseTo(1.0);
    expect(c.b).toBeCloseTo(1.0);
  });

  test("named color: transparent → alpha=0", () => {
    const c = parseCSSColor("transparent");
    expect(c.a).toBe(0);
  });

  test("hsl(120, 100%, 50%) → green", () => {
    const c = parseCSSColor("hsl(120, 100%, 50%)");
    expect(c.g).toBeCloseTo(1.0);
    expect(c.r).toBeCloseTo(0, 1);
  });

  test("無效字串回傳 null", () => {
    expect(parseCSSColor("not-a-color")).toBeNull();
    expect(parseCSSColor("")).toBeNull();
    expect(parseCSSColor(null)).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────────

describe("buildGradientPaint", () => {
  const twoStops = [
    { color: "rgba(255,0,0,1)", position: 0 },
    { color: "rgba(0,0,255,1)", position: 1 },
  ];

  test("GRADIENT_LINEAR 輸出正確類型", () => {
    const paint = buildGradientPaint({ type: "GRADIENT_LINEAR", stops: twoStops, angle: 90 });
    expect(paint).not.toBeNull();
    expect(paint.type).toBe("GRADIENT_LINEAR");
    expect(paint.gradientStops).toHaveLength(2);
  });

  test("GRADIENT_RADIAL 輸出正確類型", () => {
    const paint = buildGradientPaint({ type: "GRADIENT_RADIAL", stops: twoStops });
    expect(paint.type).toBe("GRADIENT_RADIAL");
  });

  test("GRADIENT_ANGULAR 輸出正確類型", () => {
    const paint = buildGradientPaint({ type: "GRADIENT_ANGULAR", stops: twoStops });
    expect(paint.type).toBe("GRADIENT_ANGULAR");
  });

  test("stops 少於 2 個回傳 null", () => {
    const paint = buildGradientPaint({
      type: "GRADIENT_LINEAR",
      stops: [{ color: "red", position: 0 }],
    });
    expect(paint).toBeNull();
  });

  test("stops 顏色正確轉換", () => {
    const paint = buildGradientPaint({ type: "GRADIENT_LINEAR", stops: twoStops });
    expect(paint.gradientStops[0].color.r).toBeCloseTo(1.0);
    expect(paint.gradientStops[1].color.b).toBeCloseTo(1.0);
  });

  test("LINEAR 不同角度產生不同 transform", () => {
    // 45° 與 135° 的 cos/sin 值明確不同
    const p45 = buildGradientPaint({ type: "GRADIENT_LINEAR", stops: twoStops, angle: 45 });
    const p135 = buildGradientPaint({ type: "GRADIENT_LINEAR", stops: twoStops, angle: 135 });
    expect(p45.gradientTransform).not.toEqual(p135.gradientTransform);
  });
});

// ─────────────────────────────────────────────────────────────────

describe("buildFills", () => {
  test("SOLID fill 正確輸出", () => {
    const fills = buildFills([{ type: "SOLID", color: "rgba(255,0,0,1)" }]);
    expect(fills).toHaveLength(1);
    expect(fills[0].type).toBe("SOLID");
    expect(fills[0].color.r).toBeCloseTo(1.0);
    expect(fills[0].opacity).toBe(1);
  });

  test("SOLID fill 含透明度", () => {
    const fills = buildFills([{ type: "SOLID", color: "rgba(0,0,0,0.5)" }]);
    expect(fills[0].opacity).toBe(0.5);
  });

  test("GRADIENT_LINEAR fill 輸出", () => {
    const fills = buildFills([{
      type: "GRADIENT_LINEAR",
      stops: [
        { color: "rgba(255,0,0,1)", position: 0 },
        { color: "rgba(0,0,255,1)", position: 1 },
      ],
    }]);
    expect(fills[0].type).toBe("GRADIENT_LINEAR");
  });

  test("空陣列回傳空陣列", () => {
    expect(buildFills([])).toHaveLength(0);
  });

  test("無效顏色的 SOLID 被略過", () => {
    const fills = buildFills([{ type: "SOLID", color: "not-a-color" }]);
    expect(fills).toHaveLength(0);
  });

  test("多個 fill 全部輸出", () => {
    const fills = buildFills([
      { type: "SOLID", color: "rgba(255,0,0,1)" },
      { type: "SOLID", color: "rgba(0,255,0,0.5)" },
    ]);
    expect(fills).toHaveLength(2);
  });
});

// ─────────────────────────────────────────────────────────────────

describe("buildEffects", () => {
  test("DROP_SHADOW 輸出", () => {
    const effects = buildEffects([{
      type: "DROP_SHADOW",
      color: "rgba(0,0,0,0.25)",
      offsetX: 0, offsetY: 4,
      blur: 8, spread: 0,
    }]);
    expect(effects).toHaveLength(1);
    expect(effects[0].type).toBe("DROP_SHADOW");
    expect(effects[0].radius).toBe(8);
    expect(effects[0].offset).toEqual({ x: 0, y: 4 });
  });

  test("INNER_SHADOW 輸出", () => {
    const effects = buildEffects([{
      type: "INNER_SHADOW",
      color: "rgba(0,0,0,0.3)",
      offsetX: 2, offsetY: 2,
      blur: 4, spread: 0,
    }]);
    expect(effects[0].type).toBe("INNER_SHADOW");
  });

  test("LAYER_BLUR 輸出", () => {
    const effects = buildEffects([{ type: "LAYER_BLUR", blur: 10 }]);
    expect(effects[0].type).toBe("LAYER_BLUR");
    expect(effects[0].radius).toBe(10);
    expect(effects[0].visible).toBe(true);
  });

  test("BACKGROUND_BLUR 輸出", () => {
    const effects = buildEffects([{ type: "BACKGROUND_BLUR", blur: 20 }]);
    expect(effects[0].type).toBe("BACKGROUND_BLUR");
  });

  test("空陣列回傳空陣列", () => {
    expect(buildEffects([])).toHaveLength(0);
  });

  test("多種 effect 全部輸出", () => {
    const effects = buildEffects([
      { type: "DROP_SHADOW", color: "rgba(0,0,0,0.25)", offsetX: 0, offsetY: 2, blur: 4 },
      { type: "LAYER_BLUR", blur: 8 },
    ]);
    expect(effects).toHaveLength(2);
  });
});

// ─────────────────────────────────────────────────────────────────

describe("countNodes", () => {
  test("葉節點計為 1", () => {
    expect(countNodes({ figmaName: "Leaf" })).toBe(1);
  });

  test("有 children 遞迴計算", () => {
    const tree = {
      figmaName: "Root",
      children: [
        { figmaName: "A" },
        { figmaName: "B", children: [{ figmaName: "C" }] },
      ],
    };
    expect(countNodes(tree)).toBe(4); // Root+A+B+C
  });

  test("深層巢狀正確計算", () => {
    const tree = {
      figmaName: "L0",
      children: [{ figmaName: "L1", children: [{ figmaName: "L2", children: [{ figmaName: "L3" }] }] }],
    };
    expect(countNodes(tree)).toBe(4);
  });

  test("空 children 正常運作", () => {
    expect(countNodes({ figmaName: "Node", children: [] })).toBe(1);
  });
});

/**
 * Figma Console Bridge（給 AiIRIS-pdm / aipdm figma-console 使用）
 *
 * 1. 先在本機執行：aipdm figma-console serve（預設 3055）
 * 2. Figma → Plugins → Development → Open Console
 * 3. 將本檔**整段**貼入 Console
 * 4. 代理優先連 ws://localhost:3055?role=plugin，失敗再嘗試 3001（相容舊設定）
 */

(function() {
  // 重要：避免重複貼上腳本導致多個 bridge 同時重連（會一直打舊的 3001）
  // 這裡用「全域狀態」保存 ws / timer，新的貼上會強制清掉舊實例。
  const GLOBAL_KEY = '__FIGMAI_BRIDGE__';
  const SCRIPT_VERSION = '2026-03-19-singleton-v2';

  function hardStop(state) {
    if (!state) return;
    state.stopped = true;
    try {
      if (state.reconnectTimer) {
        clearInterval(state.reconnectTimer);
        state.reconnectTimer = null;
      }
    } catch (e) {}
    try {
      if (state.ws) {
        state.ws.onopen = null;
        state.ws.onmessage = null;
        state.ws.onclose = null;
        state.ws.onerror = null;
        state.ws.close();
        state.ws = null;
      }
    } catch (e) {}
  }

  try {
    // 如果有舊 bridge，直接強制停止（不依賴舊版是否有 stop()）
    hardStop(globalThis[GLOBAL_KEY]);
  } catch (e) {}

  // 預設先連 3055（對齊 FigmAI/文件預設），失敗再 fallback 到 3001（相容舊設定）
  const state = {
    version: SCRIPT_VERSION,
    candidateUrls: ['ws://localhost:3055?role=plugin', 'ws://localhost:3001?role=plugin'],
    activeUrlIndex: 0,
    lastSuccessfulUrlIndex: null,
    hasEverConnected: false,
    ws: null,
    reconnectTimer: null,
    stopped: false,
  };

  // 註冊單例狀態，讓下次貼上腳本可以先 hardStop
  globalThis[GLOBAL_KEY] = state;

  const SERVER_URL = () => state.candidateUrls[state.activeUrlIndex];

  console.log(
    `[FigmAI Bridge] Boot ${state.version} candidates=${JSON.stringify(state.candidateUrls)} active=${state.activeUrlIndex}`
  );

  function connect() {
    if (state.stopped) return;
    const url = SERVER_URL();
    console.log(`[FigmAI Bridge] Connecting to ${url}...`);

    // 避免同時建立多個 WebSocket（例如重複貼上腳本或 timer 疊加）
    if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    state.ws = new WebSocket(url);

    state.ws.onopen = () => {
      console.log('[FigmAI Bridge] Connected! AI can now access your Figma session.');
      state.hasEverConnected = true;
      state.lastSuccessfulUrlIndex = state.activeUrlIndex;
      if (state.reconnectTimer) {
        clearInterval(state.reconnectTimer);
        state.reconnectTimer = null;
      }
    };

    state.ws.onmessage = async (event) => {
      try {
        const request = JSON.parse(event.data);
        const { id, method, params } = request;
        console.log(`[FigmAI Bridge] AI requested: ${method}`, params);
        
        let result = await handleRequest(method, params);
        state.ws.send(JSON.stringify({ id, result }));
      } catch (error) {
        console.error('[FigmAI Bridge] Request failed:', error);
        const request = JSON.parse(event.data);
        state.ws.send(JSON.stringify({ 
          id: request.id, 
          error: { message: error.message || 'Unknown error' } 
        }));
      }
    };

    state.ws.onclose = () => {
      if (state.stopped) return;
      console.warn('[FigmAI Bridge] Connection closed. Retrying in 5 seconds...');
      // 只在「尚未成功連線」的情況下才輪流嘗試不同 URL。
      // 一旦曾成功連線，後續重連會優先鎖定最後一次成功的 URL，避免一直去打另一個埠造成噪音。
      if (!state.hasEverConnected) {
        if (state.candidateUrls.length > 1) {
          state.activeUrlIndex = (state.activeUrlIndex + 1) % state.candidateUrls.length;
        }
      } else if (state.lastSuccessfulUrlIndex !== null) {
        state.activeUrlIndex = state.lastSuccessfulUrlIndex;
      }
      if (!state.reconnectTimer) {
        state.reconnectTimer = setInterval(connect, 5000);
      }
    };

    state.ws.onerror = (err) => {
      console.error('[FigmAI Bridge] WebSocket error:', err);
    };
  }

  async function handleRequest(method, params) {
    switch (method) {
      case 'getSelection':
        return figma.currentPage.selection.map(n => ({
          id: n.id,
          name: n.name,
          type: n.type
        }));

      case 'setSelection': {
        const nodes = params.nodeIds.map(id => figma.getNodeById(id)).filter(n => !!n);
        if (nodes.length > 0) {
          // If node is on another page, switch to it
          let firstNode = nodes[0];
          let parent = firstNode.parent;
          while (parent && parent.type !== 'PAGE') {
            parent = parent.parent;
          }
          if (parent && parent.type === 'PAGE' && figma.currentPage !== parent) {
            figma.currentPage = parent;
          }
          
          figma.currentPage.selection = nodes;
          figma.viewport.scrollAndZoomIntoView(nodes);
        }
        return true;
      }

      case 'getNode':
        const node = figma.getNodeById(params.nodeId);
        return node ? serializeNode(node, params.depth || 1) : null;

      case 'createNode': {
        const { type, name, props = {}, parentId } = params;
        const parent = parentId ? figma.getNodeById(parentId) : figma.currentPage;
        let newNode;

        switch (type) {
          case 'FRAME': newNode = figma.createFrame(); break;
          case 'COMPONENT': newNode = figma.createComponent(); break;
          case 'TEXT': 
            await figma.loadFontAsync({ family: "Inter", style: "Regular" });
            newNode = figma.createText(); 
            break;
          case 'RECTANGLE': newNode = figma.createRectangle(); break;
          default: throw new Error(`Type ${type} not supported for creation`);
        }

        if (name) newNode.name = name;
        
        // Get all props from params
        const { width, height, x, y, layoutMode, itemSpacing, layoutAlign, layoutGrow, ...rest } = props;

        // 1. Basic Dimensions
        if (width !== undefined || height !== undefined) {
          newNode.resize(
            width !== undefined ? width : newNode.width,
            height !== undefined ? height : newNode.height
          );
        }
        if (x !== undefined) newNode.x = x;
        if (y !== undefined) newNode.y = y;

        // 2. Responsive properties (Available on children of Auto Layout frames)
        if (layoutAlign) newNode.layoutAlign = layoutAlign;
        if (layoutGrow !== undefined) newNode.layoutGrow = layoutGrow;

        // 3. Auto Layout Page properties (For the parent frame)
        if (newNode.type === 'FRAME' && layoutMode && layoutMode !== 'NONE') {
          newNode.layoutMode = layoutMode;
          if (itemSpacing !== undefined) newNode.itemSpacing = itemSpacing;
        }

        // 4. Apply remaining properties safely
        for (const key in rest) {
          try {
            newNode[key] = rest[key];
          } catch (e) {
            console.warn(`[FigmAI Bridge] Could not set ${key} on ${newNode.type}`, e);
          }
        }

        parent.appendChild(newNode);
        return { id: newNode.id };
      }

      case 'createInstance': {
        const { componentId, parentId, props = {} } = params;
        const main = figma.getNodeById(componentId);
        if (!main || main.type !== 'COMPONENT') throw new Error(`Main component ${componentId} not found`);
        
        const instance = main.createInstance();
        const parent = parentId ? figma.getNodeById(parentId) : figma.currentPage;
        parent.appendChild(instance);

        if (props.name) instance.name = props.name;
        if (props.x !== undefined) instance.x = props.x;
        if (props.y !== undefined) instance.y = props.y;
        
        return { id: instance.id };
      }

      case 'addMarkers': {
        const { markers, parentId } = params;
        const parent = parentId ? figma.getNodeById(parentId) : figma.currentPage;
        
        // Load all necessary font variations
        await Promise.all([
          figma.loadFontAsync({ family: "Inter", style: "Regular" }),
          figma.loadFontAsync({ family: "Inter", style: "Medium" })
        ]);

        for (const m of markers) {
          // Create marker circle
          const circle = figma.createEllipse();
          circle.name = `Marker ${m.label}`;
          circle.resize(20, 20);
          circle.x = m.x - 10;
          circle.y = m.y - 10;
          circle.fills = [{ type: 'SOLID', color: { r: 1, g: 0.2, b: 0.2 } }]; // Red

          // Create text index
          const text = figma.createText();
          text.characters = m.label;
          text.fontSize = 12;
          text.fills = [{ type: 'SOLID', color: { r: 1, g: 1, b: 1 } }]; // White
          text.x = circle.x + (20 - text.width) / 2;
          text.y = circle.y + (20 - text.height) / 2;

          parent.appendChild(circle);
          parent.appendChild(text);
          figma.group([circle, text], parent).name = `Annotation ${m.label}`;
        }
        return true;
      }

      case 'getProjectInfo': {
        return {
          document: figma.root.name,
          pages: figma.root.children.map(p => ({ 
            id: p.id, 
            name: p.name,
            childrenCount: p.children.length,
            topChildren: p.children.slice(0, 10).map(c => ({ id: c.id, name: c.name }))
          }))
        };
      }

      case 'searchNodes': {
        const { pattern } = params;
        const nodes = figma.root.findAll(n => n.name.includes(pattern));
        return nodes.map(n => ({ id: n.id, name: n.name, type: n.type }));
      }

      case 'getLocalVariables': {
        // 取得此檔案中的 Local Variables（Design Tokens）
        // Figma Plugin API: figma.variables.getLocalVariablesAsync()
        if (!figma.variables?.getLocalVariablesAsync) {
          throw new Error('Figma Variables API not available in this environment.');
        }
        const vars = await figma.variables.getLocalVariablesAsync();
        return vars.map(v => ({
          id: v.id,
          name: v.name,
          resolvedType: v.resolvedType,
          valuesByMode: v.valuesByMode,
          description: v.description
        }));
      }

      case 'getLocalVariableCollections': {
        // 取得此檔案中的 Variable Collections（含 modes 與 variableIds）
        // Figma Plugin API: figma.variables.getLocalVariableCollectionsAsync()
        if (!figma.variables?.getLocalVariableCollectionsAsync) {
          throw new Error('Figma Variables API not available in this environment.');
        }
        const cols = await figma.variables.getLocalVariableCollectionsAsync();
        return cols.map(c => ({
          id: c.id,
          name: c.name,
          modes: c.modes,
          variableIds: c.variableIds
        }));
      }

      case 'updateNode': {
        const { nodeId, props = {} } = params;
        const node = figma.getNodeById(nodeId);
        if (!node) throw new Error(`Node ${nodeId} not found`);

        const { width, height, x, y, layoutMode, itemSpacing, layoutAlign, layoutGrow, ...rest } = props;

        if (width !== undefined || height !== undefined) {
          node.resize(
            width !== undefined ? width : node.width,
            height !== undefined ? height : node.height
          );
        }
        if (x !== undefined) node.x = x;
        if (y !== undefined) node.y = y;

        if (node.type === 'FRAME' && layoutMode) {
          node.layoutMode = layoutMode;
          if (itemSpacing !== undefined) node.itemSpacing = itemSpacing;
        }

        if (layoutAlign) node.layoutAlign = layoutAlign;
        if (layoutGrow !== undefined) node.layoutGrow = layoutGrow;

        for (const key in rest) {
          try {
            node[key] = rest[key];
          } catch (e) {
            console.warn(`[FigmAI Bridge] Could not update ${key}`, e);
          }
        }
        return true;
      }

      case 'deleteNode': {
        const { nodeId } = params;
        const node = figma.getNodeById(nodeId);
        if (!node) return false;
        // 不能刪除 PAGE / DOCUMENT 等根層節點
        if (!node.remove || node.type === 'PAGE' || node.type === 'DOCUMENT') {
          return false;
        }
        node.remove();
        return true;
      }

      case 'moveNode': {
        const { nodeId, parentId, index } = params;
        const node = figma.getNodeById(nodeId);
        const parent = parentId ? figma.getNodeById(parentId) : figma.currentPage;
        if (!node || !parent) return false;
        if (!('appendChild' in parent)) return false;
        parent.appendChild(node);
        if (typeof index === 'number' && 'insertChild' in parent) {
          const safeIndex = Math.max(0, Math.min(index, parent.children.length - 1));
          parent.insertChild(safeIndex, node);
        }
        return true;
      }

      case 'notify':
        figma.notify(params.message, params.options || {});
        return true;

      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  }

  function serializeNode(node, depth = 1) {
    if (!node) return null;
    const data = {
      id: node.id,
      name: node.name,
      type: node.type,
      visible: node.visible,
      parentId: node.parent?.id,
      x: node.x,
      y: node.y,
      width: node.width,
      height: node.height,
      absoluteBoundingBox: node.absoluteBoundingBox
    };

    // Extract common visual properties
    try {
      if ('fills' in node && node.fills !== figma.mixed) {
        data.fills = JSON.parse(JSON.stringify(node.fills));
      }
      if ('strokes' in node && node.strokes !== figma.mixed) {
        data.strokes = JSON.parse(JSON.stringify(node.strokes));
      }
      if ('strokeWeight' in node && node.strokeWeight !== undefined) {
        data.strokeWeight = node.strokeWeight;
      }
      if ('strokeAlign' in node && node.strokeAlign !== undefined) {
        data.strokeAlign = node.strokeAlign;
      }
      if ('strokeCap' in node && node.strokeCap !== undefined) data.strokeCap = node.strokeCap;
      if ('strokeJoin' in node && node.strokeJoin !== undefined) data.strokeJoin = node.strokeJoin;
      if ('strokeDashes' in node && Array.isArray(node.strokeDashes)) data.strokeDashes = [...node.strokeDashes];
      if (node.blendMode !== undefined) data.blendMode = node.blendMode;
      if ('effects' in node && node.effects !== figma.mixed) {
        data.effects = JSON.parse(JSON.stringify(node.effects));
      }
      if (node.opacity !== undefined) data.opacity = node.opacity;
      if (node.characters !== undefined) data.characters = node.characters;
      if (node.layoutMode !== undefined) data.layoutMode = node.layoutMode;
      if (node.layoutAlign !== undefined) data.layoutAlign = node.layoutAlign;
      if (node.layoutGrow !== undefined) data.layoutGrow = node.layoutGrow;
      if (node.primaryAxisSizingMode !== undefined) data.primaryAxisSizingMode = node.primaryAxisSizingMode;
      if (node.counterAxisSizingMode !== undefined) data.counterAxisSizingMode = node.counterAxisSizingMode;
      if (node.itemSpacing !== undefined) data.itemSpacing = node.itemSpacing;
      if (node.paddingTop !== undefined) data.paddingTop = node.paddingTop;
      if (node.paddingRight !== undefined) data.paddingRight = node.paddingRight;
      if (node.paddingBottom !== undefined) data.paddingBottom = node.paddingBottom;
      if (node.paddingLeft !== undefined) data.paddingLeft = node.paddingLeft;
      if (node.cornerRadius !== undefined) data.cornerRadius = node.cornerRadius;
      if (node.topLeftRadius !== undefined) data.topLeftRadius = node.topLeftRadius;
      if (node.topRightRadius !== undefined) data.topRightRadius = node.topRightRadius;
      if (node.bottomLeftRadius !== undefined) data.bottomLeftRadius = node.bottomLeftRadius;
      if (node.bottomRightRadius !== undefined) data.bottomRightRadius = node.bottomRightRadius;
      if (node.componentPropertyDefinitions !== undefined) data.componentPropertyDefinitions = node.componentPropertyDefinitions;
      if (node.boundVariables !== undefined) data.boundVariables = JSON.parse(JSON.stringify(node.boundVariables));

      // Text style（用於 pixel-level 一致性）
      if (node.type === 'TEXT') {
        if (node.fontName !== undefined) data.fontName = JSON.parse(JSON.stringify(node.fontName));
        if (node.fontSize !== undefined) data.fontSize = node.fontSize;
        if (node.lineHeight !== undefined) data.lineHeight = JSON.parse(JSON.stringify(node.lineHeight));
        if (node.letterSpacing !== undefined) data.letterSpacing = JSON.parse(JSON.stringify(node.letterSpacing));
        if (node.textAlignHorizontal !== undefined) data.textAlignHorizontal = node.textAlignHorizontal;
        if (node.textAlignVertical !== undefined) data.textAlignVertical = node.textAlignVertical;
      }
    } catch (e) {
      console.warn(`[FigmAI Bridge] Failed to serialize some props for ${node.id}`, e);
    }

    // Handle recursion with safety
    if (depth > 0 && 'children' in node && node.children.length > 0) {
      // Limit to first 50 children for performance if node is huge
      const childrenToProcess = node.children.slice(0, 50);
      data.children = childrenToProcess.map(c => serializeNode(c, depth - 1));
      if (node.children.length > 50) {
        data.hasMoreChildren = true;
      }
    }

    return data;
  }

  // Start the connection
  connect();
})();

// Figma 3D 变换插件 - 主线程
// 负责：选区校验、导出PNG、创建结果图片节点

async function main() {
  const selection = figma.currentPage.selection;

  if (selection.length === 0) {
    figma.notify('请先选择一个元素');
    figma.closePlugin();
    return;
  }
  if (selection.length > 1) {
    figma.notify('请只选择一个元素');
    figma.closePlugin();
    return;
  }

  const selectedNode = selection[0];

  if (!('exportAsync' in selectedNode)) {
    figma.notify('该元素类型不支持导出');
    figma.closePlugin();
    return;
  }

  // 判断是否是之前生成的 3D 变换结果（再次编辑）
  let sourceNode = selectedNode;
  let resultNode = null; // 非 null 时表示再次编辑，直接更新该节点

  const isTransformed = selectedNode.getPluginData('isTransformed3D') === 'true';
  if (isTransformed) {
    const originalId = selectedNode.getPluginData('originalNodeId');
    const originalNode = await figma.getNodeByIdAsync(originalId);
    if (originalNode && 'exportAsync' in originalNode) {
      sourceNode = originalNode;
      resultNode = selectedNode;
    } else {
      figma.notify('未找到原始元素，将对当前图片进行变换');
      // sourceNode 保持 selectedNode，当作普通元素处理
    }
  }

  let imageBytes;
  try {
    imageBytes = await sourceNode.exportAsync({
      format: 'PNG',
      constraint: { type: 'SCALE', value: 2 }
    });
  } catch (e) {
    figma.notify('导出元素失败：' + e.message);
    figma.closePlugin();
    return;
  }

  figma.showUI(__html__, {
    width: 420,
    height: 600,
    title: '3D 变换',
    themeColors: true
  });

  // 发送图片数据和尺寸到 UI（始终基于原始元素，角度从 0 开始）
  figma.ui.postMessage({
    type: 'init',
    imageBytes: imageBytes,
    width: sourceNode.width,
    height: sourceNode.height
  });

  const originalX = sourceNode.x;
  const originalY = sourceNode.y;
  const originalWidth = sourceNode.width;

  figma.ui.onmessage = async (msg) => {
    if (msg.type === 'apply') {
      try {
        const bytes = new Uint8Array(msg.imageBytes);
        const image = figma.createImage(bytes);

        let rect;
        if (resultNode) {
          // 再次编辑：更新已有节点的图片和尺寸，位置不变
          rect = resultNode;
          rect.resize(msg.width, msg.height);
          rect.fills = [{
            type: 'IMAGE',
            imageHash: image.hash,
            scaleMode: 'FILL'
          }];
        } else {
          // 首次创建：新建矩形，放在原元素右侧
          rect = figma.createRectangle();
          rect.resize(msg.width, msg.height);
          rect.x = originalX + originalWidth + 50;
          rect.y = originalY;
          rect.fills = [{
            type: 'IMAGE',
            imageHash: image.hash,
            scaleMode: 'FILL'
          }];
          rect.name = sourceNode.name + ' [3D变换]';
          figma.currentPage.appendChild(rect);

          // 记录元数据，供下次再编辑时溯源到原始元素
          rect.setPluginData('isTransformed3D', 'true');
          rect.setPluginData('originalNodeId', sourceNode.id);
        }

        figma.currentPage.selection = [rect];
        figma.viewport.scrollAndZoomIntoView([rect]);
        figma.notify('3D 变换已应用！');
      } catch (e) {
        figma.notify('应用失败：' + e.message);
      }
    }

    if (msg.type === 'cancel') {
      figma.closePlugin();
    }
  };
}

main();

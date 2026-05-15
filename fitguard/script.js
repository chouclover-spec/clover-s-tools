/* FitGuard - 游戏背景图多分辨率适配预览 */

const DESIGN = {
  bgWidth: 2720,
  bgHeight: 1440,
  uiWidth: 2560,
  uiHeight: 1440,
  safeWidth: 1920,
  safeHeight: 1080,
  padding: 80
};

const ASPECT_RATIOS = [
  { ratio: '4:3', w: 1920, h: 1440, color: '#FF6D00' },
  { ratio: '16:9', w: 2560, h: 1440, color: '#2979FF' },
  { ratio: '21:9', w: 3440, h: 1440, color: '#00C853' },
  { ratio: '32:9', w: 3840, h: 1080, color: '#F50057' }
];

let sourceImage = null;

let maskImgL = null;
let maskImgR = null;

function generateMasks() {
  const maskW = 640, maskH = 1080;
  const solidW = 560;
  const bgColor = '#0A0D14';

  const cL = document.createElement('canvas');
  cL.width = maskW; cL.height = maskH;
  const ctxL = cL.getContext('2d');
  const gL = ctxL.createLinearGradient(0, 0, maskW, 0);
  gL.addColorStop(0, bgColor);
  gL.addColorStop(solidW / maskW, bgColor);
  gL.addColorStop(1, 'rgba(10,13,20,0)');
  ctxL.fillStyle = gL;
  ctxL.fillRect(0, 0, maskW, maskH);

  const cR = document.createElement('canvas');
  cR.width = maskW; cR.height = maskH;
  const ctxR = cR.getContext('2d');
  const gR = ctxR.createLinearGradient(0, 0, maskW, 0);
  gR.addColorStop(0, 'rgba(10,13,20,0)');
  gR.addColorStop((maskW - solidW) / maskW, bgColor);
  gR.addColorStop(1, bgColor);
  ctxR.fillStyle = gR;
  ctxR.fillRect(0, 0, maskW, maskH);

  const loadDataURI = cv => new Promise(resolve => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.src = cv.toDataURL('image/png');
  });
  Promise.all([loadDataURI(cL), loadDataURI(cR)]).then(([l, r]) => {
    maskImgL = l; maskImgR = r;
  });
}
generateMasks();

const $ = id => document.getElementById(id);
const droparea = $('droparea');
const fileInput = $('fileInput');
const uploadZone = $('uploadZone');
const mainContent = $('mainContent');
const previewGrid = $('previewGrid');
const overviewSection = $('overviewSection');
const overlaySection = $('overlaySection');
const overlayCanvas = $('overlayCanvas');
const btnNewImage = $('btnNewImage');

// ---------- 上传 ----------
droparea.addEventListener('click', () => fileInput.click());
droparea.addEventListener('dragover', e => {
  e.preventDefault();
  droparea.classList.add('drag-over');
});
droparea.addEventListener('dragleave', () => droparea.classList.remove('drag-over'));
droparea.addEventListener('drop', e => {
  e.preventDefault();
  droparea.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) loadImage(file);
});
fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (file) loadImage(file);
});

function loadImage(file) {
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.onload = () => {
    URL.revokeObjectURL(url);
    sourceImage = img;
    uploadZone.classList.add('hidden');
    mainContent.classList.remove('hidden');
    renderAll();
  };
  img.onerror = () => {
    URL.revokeObjectURL(url);
    alert('图片加载失败');
  };
  img.src = url;
}

// ---------- 裁切逻辑 ----------
function getCropRect(img, ar) {
  const imgW = img.width;
  const imgH = img.height;
  const targetW = ar.w;
  const targetH = ar.h;
  const targetRatio = targetW / targetH;

  let cropX, cropY, cropW, cropH;

  if (ar.ratio === '21:9') {
    const contentW = Math.min(2560, imgW >= 2720 ? imgW - 160 : imgW);
    cropW = contentW;
    cropH = cropW / targetRatio;
    cropX = (imgW - cropW) / 2;
    cropY = (imgH - cropH) / 2;
  } else if (ar.ratio === '32:9') {
    cropW = Math.min(DESIGN.bgWidth, imgW);
    cropH = Math.min(ar.h, imgH);
    cropX = (imgW - cropW) / 2;
    cropY = (imgH - cropH) / 2;
  } else {
    const imgRatio = imgW / imgH;
    if (imgRatio > targetRatio) {
      cropH = imgH;
      cropW = imgH * targetRatio;
      cropX = (imgW - cropW) / 2;
      cropY = 0;
    } else {
      cropW = imgW;
      cropH = imgW / targetRatio;
      cropX = 0;
      cropY = (imgH - cropH) / 2;
    }
  }

  return { x: cropX, y: cropY, w: cropW, h: cropH };
}

// ---------- 32:9 遮罩绘制（遮罩在图片上方，左对齐/右对齐，不压缩） ----------
function draw32_9Masks(ctx, canvasW, canvasH, imgDrawX, imgDrawW, bgColor) {
  const fadeW = DESIGN.padding * (imgDrawW / DESIGN.bgWidth);
  const leftEnd = imgDrawX + fadeW;
  const rightStart = imgDrawX + imgDrawW - fadeW;

  if (maskImgL && maskImgR) {
    const scaleL = canvasH / maskImgL.height;
    const maskLW = maskImgL.width * scaleL;
    ctx.drawImage(maskImgL, 0, 0, maskLW, canvasH);

    const scaleR = canvasH / maskImgR.height;
    const maskRW = maskImgR.width * scaleR;
    ctx.drawImage(maskImgR, canvasW - maskRW, 0, maskRW, canvasH);
  } else {
    if (leftEnd > 0) {
      const gradL = ctx.createLinearGradient(0, 0, leftEnd, 0);
      const solidStop = imgDrawX / leftEnd;
      gradL.addColorStop(0, bgColor);
      gradL.addColorStop(Math.max(0, solidStop), bgColor);
      gradL.addColorStop(1, 'transparent');
      ctx.fillStyle = gradL;
      ctx.fillRect(0, 0, leftEnd, canvasH);
    }

    if (canvasW > rightStart) {
      const rightW = canvasW - rightStart;
      const gradR = ctx.createLinearGradient(rightStart, 0, canvasW, 0);
      const fadeStop = fadeW / rightW;
      gradR.addColorStop(0, 'transparent');
      gradR.addColorStop(Math.min(1, fadeStop), bgColor);
      gradR.addColorStop(1, bgColor);
      ctx.fillStyle = gradR;
      ctx.fillRect(rightStart, 0, rightW, canvasH);
    }
  }
}

// ---------- 渲染总览网格 ----------
function renderOverview() {
  previewGrid.innerHTML = '';
  if (!sourceImage) return;

  const thumbH = 300;

  ASPECT_RATIOS.forEach((ar, i) => {
    const crop = getCropRect(sourceImage, ar);
    let cardW, cardH;

    if (ar.ratio === '32:9') {
      cardH = thumbH;
      cardW = Math.round(thumbH * (ar.w / ar.h));
    } else {
      cardH = thumbH;
      cardW = Math.round(thumbH * (crop.w / crop.h));
    }

    const canvas = document.createElement('canvas');
    canvas.width = cardW;
    canvas.height = cardH;
    const ctx = canvas.getContext('2d');

    if (ar.ratio === '32:9') {
      const bgColor = '#0A0D14';
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, cardW, cardH);
      const imgScale = cardH / crop.h;
      const imgDrawW = crop.w * imgScale;
      const imgDrawX = (cardW - imgDrawW) / 2;
      ctx.drawImage(sourceImage, crop.x, crop.y, crop.w, crop.h, imgDrawX, 0, imgDrawW, cardH);
      draw32_9Masks(ctx, cardW, cardH, imgDrawX, imgDrawW, bgColor);
    } else {
      ctx.drawImage(sourceImage, crop.x, crop.y, crop.w, crop.h, 0, 0, cardW, cardH);
    }

    const card = document.createElement('div');
    card.className = 'preview-card';
    card.dataset.ratio = ar.ratio;
    card.innerHTML = `
      <div class="preview-card-canvas-wrap">
        <canvas width="${cardW}" height="${cardH}"></canvas>
      </div>
      <div class="preview-card-info">
        <span class="preview-card-ratio">${ar.ratio}</span>
        <span class="preview-card-res">${ar.w}×${ar.h}</span>
      </div>
    `;
    card.querySelector('canvas').getContext('2d').drawImage(canvas, 0, 0);
    previewGrid.appendChild(card);
  });
}

// ---------- 渲染叠加模式 ----------
function getSelectedOverlayRatios() {
  const selected = [];
  document.querySelectorAll('#overlayControls input[type="checkbox"]').forEach(chk => {
    if (chk.checked) {
      const ratio = chk.closest('label').dataset.ratio;
      const ar = ASPECT_RATIOS.find(a => a.ratio === ratio);
      if (ar) selected.push(ar);
    }
  });
  return selected;
}

function renderOverlay() {
  if (!sourceImage) return;

  const selectedRatios = getSelectedOverlayRatios();
  const imgW = sourceImage.width;
  const imgH = sourceImage.height;

  let designW = imgW;
  selectedRatios.forEach(ar => {
    if (ar.ratio === '32:9') {
      designW = Math.max(designW, ar.w);
    }
  });
  const designH = imgH;

  const maxDisplayW = 1200;
  const scale = Math.min(1, maxDisplayW / designW);

  overlayCanvas.width = Math.round(designW * scale);
  overlayCanvas.height = Math.round(designH * scale);

  const ctx = overlayCanvas.getContext('2d');
  ctx.fillStyle = '#0A0D14';
  ctx.fillRect(0, 0, overlayCanvas.width, overlayCanvas.height);

  const imgOffX = ((designW - imgW) / 2) * scale;
  ctx.drawImage(sourceImage, 0, 0, imgW, imgH, imgOffX, 0, imgW * scale, imgH * scale);

  selectedRatios.forEach(ar => {
    let frameX, frameY, frameW, frameH;

    if (ar.ratio === '32:9') {
      frameX = ((designW - ar.w) / 2) * scale;
      frameY = ((imgH - ar.h) / 2) * scale;
      frameW = ar.w * scale;
      frameH = ar.h * scale;
    } else {
      const crop = getCropRect(sourceImage, ar);
      frameX = imgOffX + crop.x * scale;
      frameY = crop.y * scale;
      frameW = crop.w * scale;
      frameH = crop.h * scale;
    }

    ctx.strokeStyle = ar.color;
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(frameX, frameY, frameW, frameH);
    ctx.setLineDash([]);

    ctx.font = 'bold 21px Rajdhani, sans-serif';
    ctx.fillStyle = ar.color;
    ctx.fillText(`${ar.ratio} (${ar.w}×${ar.h})`, frameX + 6, frameY + 24);
  });
}

// ---------- 工具栏 ----------
function getActiveMode() {
  return document.querySelector('.toolbar-btn.active')?.dataset.mode || 'overview';
}

document.querySelectorAll('.toolbar-btn[data-mode]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.toolbar-btn[data-mode]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const mode = btn.dataset.mode;
    if (mode === 'overview') {
      overviewSection.classList.remove('hidden');
      overlaySection.classList.add('hidden');
    } else {
      overviewSection.classList.add('hidden');
      overlaySection.classList.remove('hidden');
      renderOverlay();
    }
  });
});

btnNewImage.addEventListener('click', () => {
  sourceImage = null;
  mainContent.classList.add('hidden');
  uploadZone.classList.remove('hidden');
  fileInput.value = '';
});

// ---------- 叠加模式勾选项 ----------
document.querySelectorAll('#overlayControls input[type="checkbox"]').forEach(chk => {
  chk.addEventListener('change', () => {
    if (!overlaySection.classList.contains('hidden')) renderOverlay();
  });
});

// ---------- 窗口resize ----------
window.addEventListener('resize', () => {
  if (!sourceImage) return;
  renderOverview();
  if (getActiveMode() === 'overlay') renderOverlay();
});

function renderAll() {
  const mode = getActiveMode();
  renderOverview();
  if (mode === 'overlay') {
    overlaySection.classList.remove('hidden');
    overviewSection.classList.add('hidden');
    renderOverlay();
  } else {
    overviewSection.classList.remove('hidden');
    overlaySection.classList.add('hidden');
  }
}

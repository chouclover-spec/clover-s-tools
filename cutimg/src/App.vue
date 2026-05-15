<template>
  <div class="app-container" @dragover.prevent @drop.prevent="onDrop">
    <!-- 顶部标题栏 -->
    <header class="app-header">
      <div class="header-left">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <line x1="9" y1="3" x2="9" y2="21"/>
          <line x1="15" y1="3" x2="15" y2="21"/>
          <line x1="3" y1="9" x2="21" y2="9"/>
          <line x1="3" y1="15" x2="21" y2="15"/>
        </svg>
        <span class="app-title">CutImg</span>
        <span class="app-subtitle">图片批量裁切工具</span>
      </div>
    </header>

    <div class="main-layout">
      <!-- 左侧：图片列表 -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <span class="section-label">图片列表</span>
          <span class="image-count" v-if="images.length > 0">{{ images.length }} 张</span>
        </div>

        <!-- 拖拽/选择区 -->
        <div
          class="drop-zone"
          :class="{ active: isDragging }"
          @click="selectImages"
          @dragenter="isDragging = true"
          @dragleave="isDragging = false"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M4 16l4-4 4 4 4-6 4 6"/>
            <rect x="3" y="3" width="18" height="18" rx="2"/>
          </svg>
          <p>点击选择 或 拖拽图片到此处</p>
          <span>支持 PNG / JPG / WebP</span>
        </div>

        <!-- 图片列表 -->
        <div class="image-list" v-if="images.length > 0">
          <div
            v-for="(img, idx) in images"
            :key="img.path"
            class="image-item"
            :class="{ selected: selectedIdx === idx }"
            @click="selectImage(idx)"
          >
            <img :src="img.thumb" class="thumb" />
            <div class="image-info">
              <span class="image-name" :title="img.name">{{ img.name }}</span>
              <span class="image-size" v-if="img.width">{{ img.width }} × {{ img.height }}</span>
            </div>
            <button class="remove-btn" @click.stop="removeImage(idx)" title="移除">✕</button>
          </div>
        </div>

        <!-- 清空按钮 -->
        <button class="btn-clear" v-if="images.length > 0" @click="clearAll">清空列表</button>
      </aside>

      <!-- 中间：预览区 -->
      <main class="preview-area">
        <div class="preview-header">
          <span class="section-label">裁切预览</span>
          <span class="cut-info" v-if="selectedImage && cols > 0 && rows > 0">
            {{ cols }} × {{ rows }} = {{ cols * rows }} 块，每块约 {{ cellW }} × {{ cellH }} px
          </span>
        </div>

        <div class="preview-wrapper" v-if="selectedImage">
          <div class="canvas-container" :style="canvasContainerStyle">
            <img
              ref="previewImg"
              :src="selectedImage.thumb"
              class="preview-img"
              @load="onImgLoad"
              draggable="false"
            />
            <!-- 裁切网格线叠加层 -->
            <svg
              v-if="cols > 0 && rows > 0 && displayW && displayH"
              class="grid-overlay"
              :width="displayW"
              :height="displayH"
            >
              <!-- 竖线 -->
              <line
                v-for="i in cols - 1"
                :key="'v' + i"
                :x1="(displayW / cols) * i"
                :y1="0"
                :x2="(displayW / cols) * i"
                :y2="displayH"
                stroke="#ff4757"
                stroke-width="1.5"
                stroke-dasharray="6,3"
              />
              <!-- 横线 -->
              <line
                v-for="j in rows - 1"
                :key="'h' + j"
                :x1="0"
                :y1="(displayH / rows) * j"
                :x2="displayW"
                :y2="(displayH / rows) * j"
                stroke="#ff4757"
                stroke-width="1.5"
                stroke-dasharray="6,3"
              />
              <!-- 边框 -->
              <rect x="0.5" y="0.5" :width="displayW - 1" :height="displayH - 1" fill="none" stroke="#ff4757" stroke-width="1.5" />
              <!-- 块序号标签（左上角） -->
              <template v-for="r in rows" :key="'label-' + r">
                <text
                  v-for="c in cols"
                  :key="`${r}-${c}`"
                  :x="(displayW / cols) * (c - 1) + 5"
                  :y="(displayH / rows) * (r - 1) + 14"
                  text-anchor="start"
                  dominant-baseline="auto"
                  fill="rgba(255,71,87,0.92)"
                  font-size="12"
                  font-weight="bold"
                  font-family="sans-serif"
                >{{ (r - 1) * cols + c }}</text>
              </template>
            </svg>
          </div>
        </div>

        <!-- 空状态 -->
        <div class="empty-preview" v-else>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18M3 15h18M9 3v18M15 3v18" stroke-dasharray="4 2"/>
          </svg>
          <p>从左侧选择图片以预览裁切效果</p>
        </div>
      </main>

      <!-- 右侧：控制面板 -->
      <aside class="control-panel">
        <div class="section-label">裁切参数</div>

        <div class="param-group">
          <label class="param-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
            横向列数（X）
          </label>
          <div class="number-input-wrap">
            <button @click="cols = Math.max(0, cols - 1)">−</button>
            <input type="number" v-model.number="cols" min="0" max="100" @input="clampCols" />
            <button @click="cols = Math.min(100, cols + 1)">+</button>
          </div>
        </div>

        <div class="param-group">
          <label class="param-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="12" y1="3" x2="12" y2="21"/>
              <line x1="6" y1="3" x2="6" y2="21"/>
              <line x1="18" y1="3" x2="18" y2="21"/>
            </svg>
            纵向行数（Y）
          </label>
          <div class="number-input-wrap">
            <button @click="rows = Math.max(0, rows - 1)">−</button>
            <input type="number" v-model.number="rows" min="0" max="100" @input="clampRows" />
            <button @click="rows = Math.min(100, rows + 1)">+</button>
          </div>
        </div>

        <!-- 裁切信息 -->
        <div class="cut-summary" v-if="selectedImage && cols > 0 && rows > 0">
          <div class="summary-row">
            <span>总块数</span>
            <strong>{{ cols * rows }}</strong>
          </div>
          <div class="summary-row">
            <span>每块尺寸</span>
            <strong>{{ cellW }} × {{ cellH }} px</strong>
          </div>
        </div>

        <div class="divider"></div>

        <div class="section-label">导出设置</div>

        <!-- 导出路径 -->
        <div class="export-path-wrap">
          <div class="export-path-label">导出路径</div>
          <div class="export-path-box" @click="selectExportPath" :class="{ placeholder: !exportDir }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            </svg>
            <span :title="exportDir">{{ exportDir || '点击选择导出文件夹' }}</span>
          </div>
        </div>

        <!-- 应用到所有图片 -->
        <div class="apply-all-wrap" v-if="images.length > 1">
          <label class="checkbox-label">
            <input type="checkbox" v-model="applyToAll" />
            <span>对所有图片使用相同参数</span>
          </label>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <button
            class="btn-export"
            :disabled="!canExport"
            @click="startExport"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {{ applyToAll && images.length > 1 ? `导出全部 ${images.length} 张` : '开始裁切导出' }}
          </button>
        </div>

        <!-- 进度提示 -->
        <div class="progress-area" v-if="exporting">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
          <span class="progress-text">处理中 {{ progressDone }} / {{ progressTotal }}...</span>
        </div>

        <!-- 完成提示 -->
        <div class="done-notice" v-if="doneMsg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          {{ doneMsg }}
        </div>

        <!-- 错误提示 -->
        <div class="error-notice" v-if="errorMsg">
          ⚠ {{ errorMsg }}
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { tauriAPI as api } from './tauriAPI.js'

// 状态
const images = ref([])
const selectedIdx = ref(-1)
const cols = ref(0)
const rows = ref(0)
const exportDir = ref('')
const applyToAll = ref(true)
const isDragging = ref(false)
const exporting = ref(false)
const progressDone = ref(0)
const progressTotal = ref(0)
const doneMsg = ref('')
const errorMsg = ref('')

// 预览图尺寸
const previewImg = ref(null)
const displayW = ref(0)
const displayH = ref(0)

const selectedImage = computed(() => images.value[selectedIdx.value] ?? null)

const cellW = computed(() => {
  if (!selectedImage.value || cols.value <= 0) return 0
  return Math.floor(selectedImage.value.width / cols.value)
})
const cellH = computed(() => {
  if (!selectedImage.value || rows.value <= 0) return 0
  return Math.floor(selectedImage.value.height / rows.value)
})

const canExport = computed(() => {
  return images.value.length > 0 && cols.value > 0 && rows.value > 0 && exportDir.value && !exporting.value
})

const progressPct = computed(() => {
  if (!progressTotal.value) return 0
  return Math.round((progressDone.value / progressTotal.value) * 100)
})

const canvasContainerStyle = computed(() => ({
  position: 'relative',
  display: 'inline-block',
  lineHeight: 0,
}))

function clampCols() { if (cols.value < 0) cols.value = 0; if (cols.value > 100) cols.value = 100 }
function clampRows() { if (rows.value < 0) rows.value = 0; if (rows.value > 100) rows.value = 100 }

onMounted(async () => {
  exportDir.value = await api.getLastExportPath()
})

// 当预览图变化时更新显示尺寸
watch(selectedImage, async () => {
  await nextTick()
  updateDisplaySize()
})

function onImgLoad() {
  updateDisplaySize()
}

function updateDisplaySize() {
  if (previewImg.value) {
    displayW.value = previewImg.value.clientWidth
    displayH.value = previewImg.value.clientHeight
  }
}

// 选择图片
async function selectImages() {
  const paths = await api.selectImages()
  await addImagePaths(paths)
}

// 拖拽放入
async function onDrop(e) {
  isDragging.value = false
  const paths = Array.from(e.dataTransfer.files)
    .filter(f => /\.(png|jpg|jpeg|webp|gif)$/i.test(f.name))
    .map(f => f.path)
  await addImagePaths(paths)
}

async function addImagePaths(paths) {
  for (const p of paths) {
    if (images.value.find(i => i.path === p)) continue
    const [thumb, meta] = await Promise.all([
      api.readImageBase64(p),
      api.getImageMeta(p),
    ])
    images.value.push({
      path: p,
      name: p.split(/[\\/]/).pop(),
      thumb,
      width: meta.width,
      height: meta.height,
    })
  }
  if (selectedIdx.value === -1 && images.value.length > 0) {
    selectedIdx.value = 0
  }
  doneMsg.value = ''
  errorMsg.value = ''
}

function selectImage(idx) {
  selectedIdx.value = idx
  doneMsg.value = ''
  errorMsg.value = ''
}

function removeImage(idx) {
  images.value.splice(idx, 1)
  if (selectedIdx.value >= images.value.length) {
    selectedIdx.value = images.value.length - 1
  }
}

function clearAll() {
  images.value = []
  selectedIdx.value = -1
  doneMsg.value = ''
  errorMsg.value = ''
}

async function selectExportPath() {
  const dir = await api.selectExportPath()
  if (dir) exportDir.value = dir
}

async function startExport() {
  if (!canExport.value) return
  doneMsg.value = ''
  errorMsg.value = ''

  const targets = applyToAll.value ? images.value : [selectedImage.value]
  progressTotal.value = targets.length
  progressDone.value = 0
  exporting.value = true

  try {
    for (const img of targets) {
      await api.cutAndExport({
        filePath: img.path,
        cols: cols.value,
        rows: rows.value,
        exportDir: exportDir.value,
      })
      progressDone.value++
    }
    const total = targets.length * cols.value * rows.value
    doneMsg.value = `✓ 完成！共导出 ${total} 张图片到 ${exportDir.value}`
  } catch (e) {
    errorMsg.value = '导出失败：' + (e?.message || e)
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
* { box-sizing: border-box; }

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0f1117;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  overflow: hidden;
}

/* 顶部标题栏 */
.app-header {
  height: 52px;
  background: #161b27;
  border-bottom: 1px solid #1e2535;
  display: flex;
  align-items: center;
  padding: 0 20px;
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.logo-icon { width: 24px; height: 24px; color: #6c8efb; }
.app-title { font-size: 16px; font-weight: 700; color: #fff; }
.app-subtitle { font-size: 12px; color: #64748b; }

/* 主布局 */
.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 左侧边栏 */
.sidebar {
  width: 240px;
  min-width: 200px;
  background: #161b27;
  border-right: 1px solid #1e2535;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 8px;
}
.image-count {
  font-size: 11px;
  color: #64748b;
  background: #1e2535;
  padding: 2px 7px;
  border-radius: 10px;
}

.drop-zone {
  margin: 0 12px 10px;
  border: 1.5px dashed #2d3748;
  border-radius: 10px;
  padding: 16px 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.drop-zone:hover, .drop-zone.active {
  border-color: #6c8efb;
  background: rgba(108, 142, 251, 0.06);
}
.drop-zone svg { width: 32px; height: 32px; color: #4a5568; margin-bottom: 6px; }
.drop-zone p { font-size: 12px; color: #94a3b8; margin: 0 0 3px; }
.drop-zone span { font-size: 10px; color: #4a5568; }

.image-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}
.image-list::-webkit-scrollbar { width: 4px; }
.image-list::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 2px; }

.image-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
}
.image-item:hover { background: #1e2535; }
.image-item.selected { background: rgba(108, 142, 251, 0.15); }
.image-item.selected .image-name { color: #6c8efb; }

.thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 5px;
  border: 1px solid #2d3748;
  flex-shrink: 0;
}
.image-info { flex: 1; min-width: 0; }
.image-name {
  font-size: 11px;
  color: #cbd5e1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}
.image-size { font-size: 10px; color: #64748b; }
.remove-btn {
  background: none;
  border: none;
  color: #4a5568;
  cursor: pointer;
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 4px;
  flex-shrink: 0;
  transition: all 0.15s;
}
.remove-btn:hover { color: #ff4757; background: rgba(255, 71, 87, 0.1); }

.btn-clear {
  margin: 8px 12px 12px;
  background: none;
  border: 1px solid #2d3748;
  color: #64748b;
  border-radius: 7px;
  padding: 7px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.btn-clear:hover { border-color: #ff4757; color: #ff4757; background: rgba(255, 71, 87, 0.05); }

/* 预览区 */
.preview-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #0f1117;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px 10px;
  flex-shrink: 0;
}
.cut-info { font-size: 12px; color: #64748b; }

.preview-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 16px;
}
.preview-wrapper::-webkit-scrollbar { width: 6px; height: 6px; }
.preview-wrapper::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 3px; }

.preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
  border-radius: 4px;
  user-select: none;
}
.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.empty-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: #2d3748;
}
.empty-preview svg { width: 80px; height: 80px; }
.empty-preview p { font-size: 14px; color: #4a5568; }

/* 控制面板 */
.control-panel {
  width: 260px;
  min-width: 220px;
  background: #161b27;
  border-left: 1px solid #1e2535;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}
.control-panel::-webkit-scrollbar { width: 4px; }
.control-panel::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 2px; }

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.param-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.param-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #94a3b8;
}

.number-input-wrap {
  display: flex;
  align-items: center;
  background: #0f1117;
  border: 1px solid #2d3748;
  border-radius: 8px;
  overflow: hidden;
}
.number-input-wrap button {
  background: none;
  border: none;
  color: #64748b;
  width: 36px;
  height: 36px;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.number-input-wrap button:hover { color: #6c8efb; background: rgba(108, 142, 251, 0.1); }
.number-input-wrap input {
  flex: 1;
  background: none;
  border: none;
  color: #e2e8f0;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  outline: none;
  padding: 0;
  min-width: 0;
}
.number-input-wrap input::-webkit-outer-spin-button,
.number-input-wrap input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

.cut-summary {
  background: rgba(108, 142, 251, 0.08);
  border: 1px solid rgba(108, 142, 251, 0.2);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #94a3b8;
}
.summary-row strong { color: #6c8efb; font-size: 13px; }

.divider {
  border: none;
  border-top: 1px solid #1e2535;
  margin: 2px 0;
}

.export-path-wrap { display: flex; flex-direction: column; gap: 5px; }
.export-path-label { font-size: 12px; color: #94a3b8; }
.export-path-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #0f1117;
  border: 1px solid #2d3748;
  border-radius: 8px;
  padding: 9px 10px;
  cursor: pointer;
  transition: border-color 0.15s;
  overflow: hidden;
}
.export-path-box:hover { border-color: #6c8efb; }
.export-path-box svg { flex-shrink: 0; color: #64748b; }
.export-path-box span {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.export-path-box.placeholder span { color: #4a5568; }

.apply-all-wrap { }
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #94a3b8;
  cursor: pointer;
  user-select: none;
}
.checkbox-label input { accent-color: #6c8efb; width: 14px; height: 14px; }

.action-buttons { margin-top: 4px; }
.btn-export {
  width: 100%;
  background: linear-gradient(135deg, #6c8efb, #5b6ef0);
  border: none;
  color: #fff;
  border-radius: 10px;
  padding: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  transition: all 0.2s;
  box-shadow: 0 4px 14px rgba(108, 142, 251, 0.3);
}
.btn-export:hover:not(:disabled) {
  background: linear-gradient(135deg, #7c9dfc, #6b7ef5);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(108, 142, 251, 0.4);
}
.btn-export:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.progress-area { display: flex; flex-direction: column; gap: 6px; }
.progress-bar {
  height: 6px;
  background: #1e2535;
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6c8efb, #5b6ef0);
  border-radius: 3px;
  transition: width 0.3s;
}
.progress-text { font-size: 11px; color: #64748b; }

.done-notice {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  background: rgba(72, 199, 142, 0.1);
  border: 1px solid rgba(72, 199, 142, 0.25);
  border-radius: 8px;
  padding: 10px;
  font-size: 12px;
  color: #48c78e;
  word-break: break-all;
}
.done-notice svg { flex-shrink: 0; margin-top: 1px; }

.error-notice {
  background: rgba(255, 71, 87, 0.1);
  border: 1px solid rgba(255, 71, 87, 0.25);
  border-radius: 8px;
  padding: 10px;
  font-size: 12px;
  color: #ff4757;
  word-break: break-all;
}
</style>
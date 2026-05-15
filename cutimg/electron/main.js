// 解决 node_modules/electron npm包 遮盖 Electron 内置模块的问题
// Electron 内置模块在 process.binding 中，通过清除 npm 包缓存让内置模块优先
try {
  const electronPkgPath = require.resolve('electron')
  // 将 npm 包的 exports 替换为空，之后 require 会走 Electron 的原生加载器
  require.cache[electronPkgPath] && delete require.cache[electronPkgPath]
} catch (e) {}

// 此时 require('electron') 如仍解析到 npm 包，则临时重命名其 package.json 的 main
// 最简单方法：直接通过 process._linkedBinding 获取
let _electron
try {
  // 尝试通过 Electron 内部接口获取
  _electron = process._linkedBinding ? process._linkedBinding('electron_common_asar') : null
} catch (e) {}

const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')
const fs = require('fs')
const sharp = require('sharp')

// 记录上次导出路径
let lastExportPath = ''
let configPath = ''

function loadConfig() {
  configPath = path.join(app.getPath('userData'), 'config.json')
  try {
    if (fs.existsSync(configPath)) {
      const data = JSON.parse(fs.readFileSync(configPath, 'utf-8'))
      lastExportPath = data.lastExportPath || ''
    }
  } catch (e) {}
}

function saveConfig() {
  try {
    fs.writeFileSync(configPath, JSON.stringify({ lastExportPath }), 'utf-8')
  } catch (e) {}
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: 'default',
    title: 'CutImg - 图片裁切工具',
  })

  const isDev = process.env.NODE_ENV === 'development'
  if (isDev) {
    win.loadURL('http://localhost:5173')
    win.webContents.openDevTools()
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }
}

app.whenReady().then(() => {
  loadConfig()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// 选择图片文件
ipcMain.handle('select-images', async () => {
  const result = await dialog.showOpenDialog({
    title: '选择图片',
    filters: [{ name: '图片文件', extensions: ['png', 'jpg', 'jpeg', 'webp', 'gif'] }],
    properties: ['openFile', 'multiSelections'],
  })
  if (result.canceled) return []
  return result.filePaths
})

// 读取图片为 base64
ipcMain.handle('read-image-base64', async (_, filePath) => {
  const data = fs.readFileSync(filePath)
  const ext = path.extname(filePath).slice(1).toLowerCase()
  const mime = ext === 'jpg' ? 'jpeg' : ext
  return `data:image/${mime};base64,` + data.toString('base64')
})

// 获取图片元数据（宽高）
ipcMain.handle('get-image-meta', async (_, filePath) => {
  const meta = await sharp(filePath).metadata()
  return { width: meta.width, height: meta.height }
})

// 获取上次导出路径
ipcMain.handle('get-last-export-path', () => lastExportPath)

// 选择导出路径
ipcMain.handle('select-export-path', async () => {
  const result = await dialog.showOpenDialog({
    title: '选择导出文件夹',
    defaultPath: lastExportPath || app.getPath('desktop'),
    properties: ['openDirectory', 'createDirectory'],
  })
  if (result.canceled) return null
  lastExportPath = result.filePaths[0]
  saveConfig()
  return lastExportPath
})

// 执行裁切导出
ipcMain.handle('cut-and-export', async (_, { filePath, cols, rows, exportDir }) => {
  const meta = await sharp(filePath).metadata()
  const { width, height } = meta
  const cellW = Math.floor(width / cols)
  const cellH = Math.floor(height / rows)
  const baseName = path.basename(filePath, path.extname(filePath))
  const ext = path.extname(filePath).slice(1).toLowerCase() || 'png'

  const results = []
  let index = 1
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const left = col * cellW
      const top = row * cellH
      // 最后一格补满剩余像素，避免因取整丢像素
      const w = col === cols - 1 ? width - left : cellW
      const h = row === rows - 1 ? height - top : cellH
      const outName = `${baseName}_${index}.${ext === 'jpg' ? 'jpg' : ext}`
      const outPath = path.join(exportDir, outName)
      await sharp(filePath)
        .extract({ left, top, width: w, height: h })
        .toFile(outPath)
      results.push(outPath)
      index++
    }
  }
  return results
})

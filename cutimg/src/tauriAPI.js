/**
 * Tauri API 桥接层
 * 替代原 window.electronAPI，对上层 Vue 代码完全透明
 */
import { invoke } from '@tauri-apps/api/core'
import { open } from '@tauri-apps/plugin-dialog'

export const tauriAPI = {
  /** 弹出文件选择框，返回图片路径数组 */
  async selectImages() {
    const result = await open({
      title: '选择图片',
      multiple: true,
      filters: [
        { name: '图片文件', extensions: ['png', 'jpg', 'jpeg', 'webp', 'gif'] },
      ],
    })
    if (!result) return []
    return Array.isArray(result) ? result : [result]
  },

  /** 读取图片为 base64 data-url */
  async readImageBase64(filePath) {
    return invoke('read_image_base64', { filePath })
  },

  /** 获取图片宽高 */
  async getImageMeta(filePath) {
    return invoke('get_image_meta', { filePath })
  },

  /** 获取上次导出路径 */
  async getLastExportPath() {
    return invoke('get_last_export_path')
  },

  /** 选择导出文件夹并持久化 */
  async selectExportPath() {
    const result = await open({
      title: '选择导出文件夹',
      directory: true,
    })
    if (!result) return null
    const dir = Array.isArray(result) ? result[0] : result
    await invoke('save_export_path', { dir })
    return dir
  },

  /** 执行裁切导出，返回输出路径列表 */
  async cutAndExport({ filePath, cols, rows, exportDir }) {
    return invoke('cut_and_export', {
      opts: { file_path: filePath, cols, rows, export_dir: exportDir },
    })
  },
}

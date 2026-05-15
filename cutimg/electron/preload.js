const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  selectImages: () => ipcRenderer.invoke('select-images'),
  readImageBase64: (filePath) => ipcRenderer.invoke('read-image-base64', filePath),
  getImageMeta: (filePath) => ipcRenderer.invoke('get-image-meta', filePath),
  getLastExportPath: () => ipcRenderer.invoke('get-last-export-path'),
  selectExportPath: () => ipcRenderer.invoke('select-export-path'),
  cutAndExport: (opts) => ipcRenderer.invoke('cut-and-export', opts),
})

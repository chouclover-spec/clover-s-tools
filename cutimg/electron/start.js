const { spawn } = require('child_process')
const path = require('path')

// 获取 electron 可执行文件路径（通过 npm 包找到真实二进制）
const electronPath = require('electron')

const proc = spawn(electronPath, ['.'], {
  cwd: path.resolve(__dirname),
  env: { ...process.env, NODE_ENV: 'development' },
  stdio: 'inherit',
})

proc.on('close', (code) => {
  process.exit(code)
})

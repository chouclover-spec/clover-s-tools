@echo off
chcp 65001 > nul
echo ================================
echo 图片重命名工具 - 打包为EXE
echo ================================
echo.

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo 错误：未找到虚拟环境！
    echo 请先运行 setup.bat 创建虚拟环境
    pause
    exit /b 1
)

echo 正在安装 PyInstaller...
pip install pyinstaller

echo.
echo 正在打包程序为 EXE 文件...
pyinstaller --onefile --windowed --name="图片重命名工具" --icon=NONE image_renamer.py

echo.
echo ================================
echo 打包完成！
echo ================================
echo 可执行文件位置：dist\图片重命名工具.exe
echo.
echo 请将以下文件打包分享给用户：
echo   1. dist\图片重命名工具.exe
echo   2. 使用说明.txt
echo.
pause

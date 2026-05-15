@echo off
cd /d "%~dp0"
echo 正在创建虚拟环境...
py -m venv venv

echo 正在激活虚拟环境...
call venv\Scripts\activate.bat

echo 正在安装依赖...
pip install -r requirements.txt

echo.
echo 设置完成！现在可以运行 start.bat 启动程序
pause

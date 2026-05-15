#!/bin/bash
echo "正在创建虚拟环境..."
python3 -m venv venv

echo "正在激活虚拟环境..."
source venv/bin/activate

echo "正在安装依赖..."
pip install -r requirements.txt

echo ""
echo "设置完成！现在可以运行 start.sh 启动程序"

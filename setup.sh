#!/bin/bash

echo "打包脚本 for Windows 和 Linux"

# 打包为 Windows 单文件
echo "Building for Windows..."
pyinstaller --onefile /opt/data/ai/AInterface/main.py --name myapp.exe  # 使用绝对路径修正

# 打包为 Linux 单文件
echo "Building for Linux..."
pyinstaller --onefile /opt/data/ai/AInterface/main.py --name myapp  # 使用绝对路径修正

echo "打包完成"
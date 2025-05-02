#!/bin/bash

echo "打包脚本 for Windows and Linux"

echo "Building for Windows..."
pyinstaller ainterface.exe.spec
echo "Building for Linux..."
pyinstaller ainterface.spec

echo "打包完成"

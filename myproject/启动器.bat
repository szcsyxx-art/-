@echo off
chcp 65001
echo.
echo ========================================
echo    🚀 网站启动器 - U盘
echo ========================================
echo.
echo 正在检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到Python，正在尝试安装...
    powershell -Command "Start-Process python -ArgumentList 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -Wait"
    echo ✅ Python安装完成，请重新运行此脚本
    pause
    exit
)

echo ✅ Python环境就绪
echo 正在安装依赖...
pip install -r requirements.txt

echo 正在启动网站...
cd /d %~dp0
python app.py

pause
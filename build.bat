@echo off
chcp 65001 >nul
echo ========================================
echo   Google Refresh Token - 本地打包工具
echo ========================================
echo.

echo [1/2] 检查 PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller 未安装，正在安装...
    pip install pyinstaller
)
echo PyInstaller 已就绪

echo.
echo [2/2] 开始打包 Windows 版...
pyinstaller --onefile --windowed --name "GoogleRefreshToken" --add-data "index.html;." main.py

if %errorlevel% neq 0 (
    echo.
    echo 打包失败！请检查错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo   exe 文件位于: dist\GoogleRefreshToken.exe
echo ========================================
echo.
pause
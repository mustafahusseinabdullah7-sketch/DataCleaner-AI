@echo off
chcp 65001 >nul
title DataCleaner AI — Starting...
color 0B

echo.
echo  ============================================
echo   DataCleaner AI ^| Local Version
echo  ============================================
echo.

:: Check Python
py --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python غير موجود. قم بتثبيته من python.org
    pause
    exit
)

:: Navigate to project root
cd /d "%~dp0"

:: Install dependencies if needed
echo  [1/3] التحقق من المكتبات...
py -m pip install -r requirements.txt -q

:: Start server
echo  [2/3] تشغيل السيرفر...
echo.
echo  ============================================
echo   التطبيق يعمل على: http://127.0.0.1:8000/app
echo   اضغط Ctrl+C لإيقاف التطبيق
echo  ============================================
echo.

:: Open browser automatically
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000/app

:: Run FastAPI server
cd backend
py -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

pause

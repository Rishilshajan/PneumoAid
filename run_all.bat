@echo off
echo ============================================
echo  Starting PneumoAid - Admin Panel (Port 5000)
echo ============================================
start cmd /k "py Admin/app.py"

echo ============================================
echo  Starting PneumoAid - Pneumo App (Port 5001)
echo ============================================
start cmd /k "Pneumo\.venv\Scripts\python.exe Pneumo/app.py"

echo.
echo Both applications are starting in separate windows.
echo   Admin   : http://127.0.0.1:5000
echo   Pneumo  : http://127.0.0.1:5001
echo.
pause

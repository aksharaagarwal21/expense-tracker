@echo off
echo ============================================
echo   Spendly Full-Stack Setup
echo ============================================
echo.

cd /d "%~dp0backend"

echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed. Make sure Python is installed.
    pause & exit /b 1
)

echo.
echo [2/4] Setting up database...
echo Make sure MySQL is running and you have updated MYSQL_PASSWORD in backend\.env
echo.
echo Creating database 'spendly' in MySQL...
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS spendly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>nul
if errorlevel 1 (
    echo WARNING: Could not auto-create database. Please run this SQL manually:
    echo   CREATE DATABASE spendly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
)

echo.
echo [3/4] Creating database tables...
python app.py &
timeout /t 3 /nobreak >nul
taskkill /f /im python.exe >nul 2>&1
python -c "from app import create_app; from config.database import db; app = create_app(); ctx = app.app_context(); ctx.push(); db.create_all(); print('Tables created!'); ctx.pop()"

echo.
echo [4/4] Setup complete!
echo.
echo ============================================
echo  HOW TO RUN:
echo  1. Open terminal in 'backend' folder
echo  2. Run: python app.py
echo  3. Open frontend\index.html in browser
echo ============================================
echo.
pause

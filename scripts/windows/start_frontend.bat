@echo off
chcp 65001 > nul

echo ========================================
echo   Legal Rent AI - Frontend (React)
echo ========================================
echo.

cd /d "%~dp0..\..\frontend"

if not exist "node_modules\" (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
    echo.
)

echo Starting Vite dev server...
echo Open your browser at: http://localhost:3000
echo.

call npm run dev

pause

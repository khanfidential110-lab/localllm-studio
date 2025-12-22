@echo off
REM ============================================================================
REM LocalLLM Studio - Windows Build Script
REM Creates a self-contained .exe that works on any Windows PC
REM ============================================================================

setlocal EnableDelayedExpansion

set APP_NAME=LocalLLM Studio
set VERSION=1.0.0
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set DIST_DIR=%PROJECT_DIR%\dist
set BUILD_DIR=%PROJECT_DIR%\build

echo ==============================================
echo   Building %APP_NAME% v%VERSION% for Windows
echo ==============================================

cd /d "%PROJECT_DIR%"

REM Step 1: Check for Python
echo.
echo [1/5] Checking Python...
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python is required to build
    echo Please install Python from https://python.org
    exit /b 1
)

REM Step 2: Create virtual environment
echo.
echo [2/5] Setting up build environment...
if not exist "build_venv" (
    python -m venv build_venv
)
call build_venv\Scripts\activate.bat

REM Step 3: Install dependencies
echo.
echo [3/5] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM Step 4: Clean previous builds
echo.
echo [4/5] Cleaning previous builds...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%DIST_DIR%"

REM Step 5: Build with PyInstaller
echo.
echo [5/5] Building application...
pyinstaller localllm_studio.spec --noconfirm

REM Verify build
if exist "%DIST_DIR%\LocalLLM Studio.exe" (
    echo.
    echo ==============================================
    echo   BUILD SUCCESSFUL!
    echo ==============================================
    echo.
    echo   Output: %DIST_DIR%\LocalLLM Studio.exe
    echo.
    echo   To run: Double-click the .exe file
    echo.
) else (
    echo.
    echo ==============================================
    echo   BUILD FAILED
    echo ==============================================
    exit /b 1
)

call deactivate
endlocal

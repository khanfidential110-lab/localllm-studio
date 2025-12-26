@echo off
REM ============================================================================
REM LocalLLM Studio - Windows Complete Setup
REM Automatically installs Python, dependencies, and builds the application
REM ============================================================================

setlocal EnableDelayedExpansion

set APP_NAME=LocalLLM Studio
set PYTHON_VERSION=3.11.7
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe

echo ==============================================
echo   %APP_NAME% - Complete Setup for Windows
echo ==============================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] Not running as Administrator.
    echo           Some features may require admin rights.
    echo.
)

REM ============================================
REM Step 1: Check/Install Python
REM ============================================
echo [1/5] Checking Python installation...

where python >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo Python not found! Installing Python %PYTHON_VERSION%...
    echo.
    
    REM Download Python installer
    echo Downloading Python installer...
    powershell -Command "& {Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile 'python_installer.exe'}"
    
    if not exist python_installer.exe (
        echo [ERROR] Failed to download Python installer.
        echo Please install Python manually from https://python.org
        pause
        exit /b 1
    )
    
    REM Install Python silently
    echo Installing Python (this may take a few minutes)...
    python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0
    
    REM Clean up
    del python_installer.exe
    
    REM Refresh PATH
    set "PATH=%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%PATH%"
    
    echo Python installed successfully!
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
    echo Python !PYVER! found.
)

REM Verify Python works
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Python installation failed.
    echo Please restart your terminal or install Python manually.
    pause
    exit /b 1
)

REM ============================================
REM Step 2: Upgrade pip
REM ============================================
echo.
echo [2/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM ============================================
REM Step 3: Install dependencies
REM ============================================
echo.
echo [3/5] Installing dependencies (this may take several minutes)...

REM Install with pre-built wheels for llama-cpp-python
python -m pip install flask huggingface-hub requests pywebview --quiet

echo Installing llama-cpp-python (pre-built wheel)...
python -m pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --quiet

if %errorLevel% neq 0 (
    echo.
    echo [WARNING] Pre-built wheel failed, trying to build from source...
    echo This requires Visual Studio Build Tools.
    echo.
    
    REM Try building from source
    python -m pip install llama-cpp-python --no-cache-dir
    
    if %errorLevel% neq 0 (
        echo.
        echo [ERROR] llama-cpp-python installation failed.
        echo.
        echo Please install Visual Studio Build Tools from:
        echo https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo.
        echo Then run this script again.
        pause
        exit /b 1
    )
)

REM Install PyInstaller for building
python -m pip install pyinstaller --quiet

echo Dependencies installed successfully!

REM ============================================
REM Step 4: Build the application
REM ============================================
echo.
echo [4/5] Building %APP_NAME%...

python -m PyInstaller localllm_studio.spec --noconfirm

if %errorLevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

REM ============================================
REM Step 5: Create shortcut
REM ============================================
echo.
echo [5/5] Creating desktop shortcut...

set SCRIPT_DIR=%~dp0
set EXE_PATH=%SCRIPT_DIR%dist\LocalLLM Studio.exe

if exist "%EXE_PATH%" (
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\LocalLLM Studio.lnk'); $s.TargetPath = '%EXE_PATH%'; $s.Save()"
    echo Desktop shortcut created!
)

echo.
echo ==============================================
echo   BUILD COMPLETE!
echo ==============================================
echo.
echo   Application: dist\LocalLLM Studio.exe
echo   Shortcut: Desktop\LocalLLM Studio.lnk
echo.
echo   Double-click to run the app!
echo.

pause

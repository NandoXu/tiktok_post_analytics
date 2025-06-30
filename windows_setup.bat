@echo off
REM --- Windows Batch Script to Install Python 3.11 and Dependencies ---

echo.
echo Attempting to install Python 3.11 and application dependencies.
echo This script requires administrative privileges for Python installation.
echo Please ensure you have an active internet connection.
echo.

REM --- 1. Check if Python 3.11 is already installed ---
echo Checking for Python 3.11...
python -c "import sys; exit(sys.version_info.major != 3 or sys.version_info.minor != 11)" 2>nul
if %errorlevel% equ 0 (
    echo Python 3.11 is already installed. Skipping direct Python installation.
) else (
    echo Python 3.11 not found. Attempting to install it.
    echo Downloading Python 3.11 installer...
    REM Using curl to download the installer. If curl is not available, manual download is needed.
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    if %errorlevel% neq 0 (
        echo Error: Failed to download Python installer. Please download manually from python.org.
        pause
        exit /b 1
    )
    echo Running Python 3.11 installer silently...
    REM /quiet: Suppresses UI
    REM InstallAllUsers=1: Installs for all users
    REM PrependPath=1: Adds Python to PATH
    REM Shortcuts=0: No desktop/start menu shortcuts
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Shortcuts=0
    if %errorlevel% neq 0 (
        echo Error: Python 3.11 installation failed. You might need to run this script as Administrator or install Python manually.
        pause
        exit /b 1
    )
    echo Python 3.11 installed.
    REM Clean up installer
    del python_installer.exe
    
    REM Re-check Python version to ensure it's available in PATH for current session
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo Warning: Python might not be immediately available in PATH after silent install. Restarting terminal might be needed.
        echo Attempting to set PATH for current session...
        REM This part is tricky to get right for all silent installs.
        REM For simplicity, we'll assume it will be picked up by the venv creation.
    )
)

REM --- Ensure Python is accessible for the current session (after fresh install) ---
REM This is crucial for newly installed Python to be found by 'python -m venv'
set PATH=%PATH%;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Critical Error: Python 3.11 is not found in PATH even after attempting to set it.
    echo Please restart your command prompt or install Python manually.
    pause
    exit /b 1
)
echo Python 3.11 found in PATH.

REM --- 2. Create a Python Virtual Environment ---
echo Creating or updating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Error: Failed to create virtual environment.
    pause
    exit /b 1
)
echo Virtual environment created.

REM --- 3. Activate the Virtual Environment ---
echo Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo Virtual environment activated.

REM --- 4. Install Python Dependencies from requirements.txt ---
echo Installing Python dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install Python dependencies.
    pause
    exit /b 1
)
echo Python dependencies installed.

REM --- 5. Install Playwright Browser Binaries ---
echo Installing Playwright browser binaries...
playwright install
if %errorlevel% neq 0 (
    echo Error: Failed to install Playwright browsers. Please ensure an active internet connection.
    pause
    exit /b 1
)
echo Playwright browsers installed.

echo.
echo Setup complete. You can now run your application using:
echo    venv\Scripts\python tiktok_post_analytics.py
echo.
pause

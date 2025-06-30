#!/bin/bash
# --- macOS/Linux Shell Script to Install Python 3.11 and Dependencies ---

echo ""
echo "Attempting to install Python 3.11 and application dependencies."
echo "This script might require 'sudo' password for system package installations."
echo "Please ensure you have an active internet connection."
echo ""

# --- 1. Check if Python 3.11 is already installed ---
echo "Checking for Python 3.11..."
if command -v python3.11 &>/dev/null; then
    echo "Python 3.11 is already installed. Skipping direct Python installation."
else
    echo "Python 3.11 not found. Attempting to install it."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS using Homebrew
        if command -v brew &>/dev/null; then
            echo "Homebrew detected. Installing Python 3.11 via Homebrew..."
            brew install python@3.11
            if [ $? -ne 0 ]; then
                echo "Error: Homebrew Python 3.11 installation failed."
                echo "Please try 'brew update' and then 'brew install python@3.11' manually, or check Homebrew setup."
                exit 1
            fi
            # Ensure Python 3.11 is linked and prioritized
            brew link python@3.11 --force --overwrite
        else
            echo "Error: Homebrew not found. Please install Homebrew (https://brew.sh/) or install Python 3.11 manually."
            exit 1
        fi
    elif [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
        # Debian/Ubuntu using apt
        echo "Debian/Ubuntu detected. Installing Python 3.11 via apt..."
        sudo apt update
        sudo apt install -y software-properties-common
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt update
        sudo apt install -y python3.11 python3.11-venv python3.11-distutils python3.11-dev
        if [ $? -ne 0 ]; then
            echo "Error: apt Python 3.11 installation failed."
            echo "Please run 'sudo apt update' and 'sudo apt install python3.11' manually."
            exit 1
        fi
    else
        echo "Error: Unsupported Linux distribution or package manager for automated Python 3.11 installation."
        echo "Please install Python 3.11 manually from python.org or your distribution's package manager."
        exit 1
    fi
    echo "Python 3.11 installation initiated. Verifying..."
    # Ensure the correct python3.11 is in PATH for subsequent steps
    PATH="/usr/bin:/usr/local/bin:$PATH" # Add common Python 3.11 paths to front of PATH
    if ! command -v python3.11 &>/dev/null; then
        echo "Critical Error: Python 3.11 is not found in PATH after installation attempt."
        echo "Please ensure it's installed correctly and in your PATH, or try installing manually."
        exit 1
    fi
    echo "Python 3.11 is now accessible."
fi

# --- 2. Create a Python Virtual Environment using python3.11 ---
echo "Creating or updating virtual environment 'venv' using python3.11..."
python3.11 -m venv venv
if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment."
    echo "Ensure 'python3.11' is correctly installed and its venv module is available."
    exit 1
fi
echo "Virtual environment created."

# --- 3. Activate the Virtual Environment ---
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment."
    exit 1
fi
echo "Virtual environment activated."

# --- 4. Install Python Dependencies from requirements.txt ---
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies."
    exit 1
fi
echo "Python dependencies installed."

# --- 5. Install Playwright Browser Binaries ---
echo "Installing Playwright browser binaries..."
playwright install
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Playwright browsers. Please ensure an active internet connection."
    exit 1
fi
echo "Playwright browsers installed."

echo ""
echo "Setup complete."
echo "To run your application, navigate to this directory and use:"
echo "    source venv/bin/activate"
echo "    python tiktok_post_analytics.py"
echo ""

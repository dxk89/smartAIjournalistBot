#!/usr/bin/env bash
# exit on any error
set -o errexit

# FIX: Change to the directory where the script is located. This makes the
# script self-contained and ensures all relative paths work correctly.
cd "$(dirname "$0")"

# --- INSTALL PYTHON DEPENDENCIES ---
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

# --- ENVIRONMENT AND CHROME SETUP ---
STORAGE_DIR="/opt/render/project/.render"
CHROME_VERSION="124.0.6367.60" # A recent stable version

# --- CHROME INSTALLATION ---
CHROME_DIR="$STORAGE_DIR/chrome"
if [[ ! -d "$CHROME_DIR/chrome-linux64" ]]; then
  echo "...Installing Chrome v${CHROME_VERSION}"
  mkdir -p "$CHROME_DIR"
  cd "$CHROME_DIR"
  wget -q -O chrome-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip"
  unzip -q chrome-linux64.zip
  rm chrome-linux64.zip
  chmod +x "$CHROME_DIR/chrome-linux64/chrome"
  cd - >/dev/null # Go back to the previous directory
else
  echo "...Using cached Chrome"
fi

# --- CHROMEDRIVER INSTALLATION ---
DRIVER_DIR="$STORAGE_DIR/chromedriver"
if [[ ! -f "$DRIVER_DIR/chromedriver" ]]; then
  echo "...Installing ChromeDriver v${CHROME_VERSION}"
  mkdir -p "$DRIVER_DIR"
  cd "$DRIVER_DIR"
  wget -q -O chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"
  unzip -q chromedriver-linux64.zip
  # The chromedriver is now inside a nested directory, adjust the move command
  mv chromedriver-linux64/chromedriver .
  rm -rf chromedriver-linux64 chromedriver-linux64.zip
  chmod +x "$DRIVER_DIR/chromedriver"
  cd - >/dev/null # Go back to the previous directory
else
  echo "...Using cached ChromeDriver"
fi

# --- STYLE GURU SETUP ---
echo "Running Style Guru setup..."
if [ -f "setup_style_guru.py" ]; then
    pip install -r requirements.txt # Re-install in case Style Guru has other dependencies
    python3.12 setup_style_guru.py
else
    echo "⚠️  setup_style_guru.py not found, skipping..."
fi

# --- CREATE .env FILES ---
echo "Creating .env files with executable paths..."

# Create .env in multiple locations to ensure it's found
ENV_CONTENT="GOOGLE_CHROME_BIN=$CHROME_DIR/chrome-linux64/chrome
CHROMEDRIVER_PATH=$DRIVER_DIR/chromedriver
CHROME_BIN=$CHROME_DIR/chrome-linux64/chrome"

# Location 1: Current directory (my_framework)
echo "$ENV_CONTENT" > ".env"
echo "✅ Created .env in my_framework/"

# Location 2: App directory
echo "$ENV_CONTENT" > "app/.env"
echo "✅ Created .env in my_framework/app/"

# Location 3: Parent directory
echo "$ENV_CONTENT" > "../.env"
echo "✅ Created .env in project root/"

# Verify the files were created
echo "Verifying Chrome installation:"
if [ -f "$CHROME_DIR/chrome-linux64/chrome" ]; then
    echo "✅ Chrome binary exists at: $CHROME_DIR/chrome-linux64/chrome"
else
    echo "❌ Chrome binary NOT found at: $CHROME_DIR/chrome-linux64/chrome"
fi

if [ -f "$DRIVER_DIR/chromedriver" ]; then
    echo "✅ ChromeDriver exists at: $DRIVER_DIR/chromedriver"
else
    echo "❌ ChromeDriver NOT found at: $DRIVER_DIR/chromedriver"
fi

echo "=========================================="
echo "Build script finished successfully."
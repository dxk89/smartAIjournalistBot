#!/usr/bin/env bash
# exit on any error
set -o errexit

# --- INSTALL PYTHON DEPENDENCIES ---
echo "Installing Python dependencies from requirements.txt..."
python3.12 -m pip install -r requirements.txt

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
else
  echo "...Using cached ChromeDriver"
fi

# Change back to the my_framework directory to continue the script
cd /opt/render/project/src/my_framework

# --- STYLE GURU SETUP ---
echo "Running Style Guru setup..."
if [ -f "setup_style_guru.py" ]; then
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

# Final verification
echo "=========================================="
echo "BUILD VERIFICATION"
echo "=========================================="
echo "Storage directory: $STORAGE_DIR"
echo "Chrome directory: $CHROME_DIR"
echo "Driver directory: $DRIVER_DIR"
echo ""

if [ -d "$STORAGE_DIR" ]; then
    echo "Contents of $STORAGE_DIR:"
    ls -la "$STORAGE_DIR" || echo "Cannot list $STORAGE_DIR"
    echo ""
fi

if [ -d "$CHROME_DIR" ]; then
    echo "Contents of $CHROME_DIR:"
    ls -la "$CHROME_DIR" || echo "Cannot list $CHROME_DIR"
    echo ""
fi

if [ -d "$CHROME_DIR/chrome-linux64" ]; then
    echo "Contents of $CHROME_DIR/chrome-linux64:"
    ls -la "$CHROME_DIR/chrome-linux64" | head -20 || echo "Cannot list chrome-linux64"
    echo ""
fi

if [ -d "$DRIVER_DIR" ]; then
    echo "Contents of $DRIVER_DIR:"
    ls -la "$DRIVER_DIR" || echo "Cannot list $DRIVER_DIR"
    echo ""
fi

echo "Checking if Chrome binary is executable:"
if [ -x "$CHROME_DIR/chrome-linux64/chrome" ]; then
    echo "✅ Chrome binary exists and is executable"
else
    echo "❌ Chrome binary missing or not executable"
fi

echo "Checking if ChromeDriver is executable:"
if [ -x "$DRIVER_DIR/chromedriver" ]; then
    echo "✅ ChromeDriver exists and is executable"
else
    echo "❌ ChromeDriver missing or not executable"
fi

echo "=========================================="
echo "Build script finished successfully."
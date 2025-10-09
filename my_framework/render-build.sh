#!/usr/bin/env bash
# exit on any error
set -o errexit

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
else
  echo "...Using cached Chrome"
fi
cd /opt/render/project/src # Go back to the original directory

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
cd /opt/render/project/src # Go back to the original directory

# --- STYLE GURU SETUP ---
echo "Running Style Guru setup..."
python setup_style_guru.py

# --- CREATE .env FILE ---
echo "Creating .env file with executable paths..."
# This ensures the application can find the installed Chrome and ChromeDriver
cat <<EOF > "/opt/render/project/src/my_framework/.env"
GOOGLE_CHROME_BIN="$CHROME_DIR/chrome-linux64/chrome"
CHROMEDRIVER_PATH="$DRIVER_DIR/chromedriver"
EOF

echo "Build script finished successfully."
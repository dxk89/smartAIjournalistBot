@echo off
setlocal

:: Change directory to the folder where the script is located
cd /d "%~dp0"
echo Running from: %cd%

:: Check if this is a Git repository
if not exist ".git" (
    echo.
    echo ERROR: This is not a Git repository.
    echo Please follow the one-time setup instructions to initialize Git.
    echo.
    pause
    exit /b
)

:: Create or update .gitignore to exclude sensitive files
echo Checking .gitignore for sensitive files...
if not exist ".gitignore" (
    echo Creating .gitignore...
    (
        echo # Credentials and sensitive files
        echo .env
        echo *.env
        echo gcp_credentials.json
        echo **/gcp_credentials.json
        echo **/.env
        echo.
        echo # API Keys
        echo **/api_keys.json
        echo credentials.json
        echo.
        echo # Python
        echo __pycache__/
        echo *.pyc
        echo *.pyo
        echo venv/
        echo env/
    ) > .gitignore
    echo .gitignore created!
) else (
    findstr /C:".env" .gitignore >nul || echo .env >> .gitignore
    findstr /C:"gcp_credentials.json" .gitignore >nul || echo gcp_credentials.json >> .gitignore
    findstr /C:"**/.env" .gitignore >nul || echo **/.env >> .gitignore
    findstr /C:"**/gcp_credentials.json" .gitignore >nul || echo **/gcp_credentials.json >> .gitignore
)
echo.

echo ===============================================
echo  UPLOADING CHANGES TO GITHUB
echo ===============================================
echo.

:: Remove nested git repository in my_framework if it exists
if exist "my_framework\.git" (
    echo Fixing nested Git repository issue...
    rd /s /q "my_framework\.git"
    git rm --cached -r my_framework 2>nul
    echo Fixed!
    echo.
)

:: Add all new and modified files to be uploaded
git add .
echo All changes have been prepared for upload.
echo.

:: Ask for a commit message
set /p commitMessage="Enter a short description for this upload: "

:: Save the changes with your description
git commit -m "%commitMessage%"
if errorlevel 1 (
    echo.
    echo No changes to commit or commit failed.
    echo.
    pause
    exit /b
)
echo.

:: Push the changes to the 'main' branch on GitHub
echo Uploading to GitHub...
git push origin main
if errorlevel 1 (
    echo.
    echo ERROR: Push failed. Check your internet connection and GitHub credentials.
    echo.
    pause
    exit /b
)
echo.

echo ===============================================
echo  UPLOAD COMPLETE!
echo ===============================================
echo.
pause
endlocal
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

echo ===============================================
echo  UPLOADING CHANGES TO GITHUB
echo ===============================================
echo.

:: Add all new and modified files to be uploaded
git add .
echo All changes have been prepared for upload.
echo.

:: Ask for a commit message
set /p commitMessage="Enter a short description for this upload: "

:: Save the changes with your description
git commit -m "%commitMessage%"
echo.

:: Push the changes to the 'main' branch on GitHub
echo Uploading to GitHub...
git push origin main
echo.

echo ===============================================
echo  UPLOAD COMPLETE!
echo ===============================================
echo.
pause
endlocal
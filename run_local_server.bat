@echo off
:: This script should be run from the root of your project folder 
:: (e.g., 'my-journalist-project - Copy')

echo =======================================================
echo  STARTING THE AI JOURNALIST SERVER
echo =======================================================
echo.

:: Change to the my_framework directory
cd my_framework

:: Set the PYTHONPATH to the 'src' directory, where your 'my_framework' package lives.
set "PYTHONPATH=%cd%\src"
echo  PYTHONPATH set to: %PYTHONPATH%
echo.

echo  This will start the main server for the multi-agent system.
echo  Once it says 'Application startup complete', open your
echo  web browser and go to: http://127.0.0.1:8000
echo.
echo  Press CTRL+C in this window to stop the server.
echo.
echo =======================================================
echo.

:: Run uvicorn from the my_framework directory
uvicorn app.server:app --reload

echo.
echo Server stopped.
echo.
pause
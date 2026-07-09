@echo off
echo Waiting 2 seconds for port to settle...
timeout /t 2 /nobreak >nul
echo.
echo Uploading Golf Swing Analyzer firmware...
echo.
C:\Users\sjfla\.platformio\penv\Scripts\platformio.exe run --target upload
pause

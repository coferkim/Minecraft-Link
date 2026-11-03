@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0MinecraftLink.exe" (
  echo MinecraftLink.exe is missing. Extract the entire release archive first.
  pause
  exit /b 1
)
echo Starting Minecraft-Link. This window shows live logs.
echo Close this window to stop the service.
"%~dp0MinecraftLink.exe"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Minecraft-Link stopped with exit code %EXIT_CODE%.
  pause
)
exit /b %EXIT_CODE%

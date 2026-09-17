@echo off
cd /d "%~dp0"
echo Starting library app...
echo.
"%~dp0..\.venv\Scripts\python.exe" -m streamlit run view_library.py --server.address=0.0.0.0
echo.
echo ============================================
echo The app stopped or failed to start. See any error message above.
echo ============================================
pause

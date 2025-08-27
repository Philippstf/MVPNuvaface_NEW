@echo off
echo Installing Gemini dependencies...

REM Check if virtual environment exists
if not exist "gemini_env" (
    echo Creating virtual environment...
    python -m venv gemini_env
)

REM Activate virtual environment
call gemini_env\Scripts\activate.bat

echo Installing required packages...
pip install --upgrade pip
pip install google-genai
pip install pillow
pip install python-dotenv

echo.
echo Installation complete!
echo.
echo IMPORTANT: Make sure you have your GOOGLE_API_KEY in the .env file.
echo.
pause
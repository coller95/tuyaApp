#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/env"
APP_FILE="$SCRIPT_DIR/app.py"

echo "Script is located at: $SCRIPT_DIR"
echo "Looking for virtual environment at: $VENV_DIR"
echo "Looking for application file at: $APP_FILE"

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment directory '$VENV_DIR' found."
    
    if [ -f "$VENV_DIR/bin/activate" ]; then
        echo "Activating virtual environment..."
        source "$VENV_DIR/bin/activate"
        echo "Virtual environment activated."
        
        if [ -f "$APP_FILE" ]; then
            # Start browser in background after delay
            BROWSER_URL="http://127.0.0.1:5000"
            echo "Browser will open automatically in 3 seconds at: $BROWSER_URL"
            (
                sleep 1
                if command -v xdg-open &> /dev/null; then
                    xdg-open "$BROWSER_URL" &> /dev/null
                elif command -v open &> /dev/null; then
                    open "$BROWSER_URL" &> /dev/null  # macOS support
                else
                    echo "Please open your browser manually: $BROWSER_URL"
                fi
            ) &
            
            # Run server in foreground (blocks script)
            echo "Starting Python application..."
            python "$APP_FILE"
            
            # Cleanup after server stops
            echo "Server stopped."
        else
            echo "Error: Application file '$APP_FILE' not found."
        fi
    else
        echo "Error: 'activate' script not found in '$VENV_DIR/bin/'."
    fi
else
    echo "Error: Virtual environment directory '$VENV_DIR' not found."
fi

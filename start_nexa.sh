#!/bin/bash
# Start Nexa backend server

# Get the absolute path of the directory containing this script
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Cleaning up lingering Nexa processes..."
pkill -f "python main.py" 2>/dev/null
pkill -f "python ui/orb_widget.py" 2>/dev/null

echo "Starting Nexa..."
cd "$PROJECT_DIR/backend" || exit

# Run the main FastAPI application in the background using the venv explicitly
echo "Starting FastAPI Backend..."
if [ -f "venv/bin/python" ]; then
    venv/bin/python main.py &
else
    python3 main.py &
fi
BACKEND_PID=$!

# Wait a second to let the server start
sleep 2

# Start the Floating Orb UI
echo "Starting Floating Orb UI..."
export PYTHONPATH="$PROJECT_DIR/backend"
if [ -f "venv/bin/python" ]; then
    venv/bin/python ui/orb_widget.py
else
    python3 ui/orb_widget.py
fi

# When the UI is closed, cleanly kill the background process if it is still running
kill $BACKEND_PID 2>/dev/null

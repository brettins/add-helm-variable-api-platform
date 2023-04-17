#!/bin/bash

# Check if Python 3 is installed
if command -v python3 &>/dev/null; then
    python_command="python3"
else
    # Python 3 is not installed, check if Python 2 is installed
    if command -v python &>/dev/null; then
        python_command="python"
    else
        echo "Python is not installed on this system."
        exit 1
    fi
fi

# Run the Python script with the detected Python version
"$python_command" addHelmVariable.py


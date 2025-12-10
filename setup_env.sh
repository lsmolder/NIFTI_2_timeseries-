#!/bin/bash

# Define the name of the virtual environment
VENV_NAME="venv"

echo "Creating virtual environment: $VENV_NAME..."
python3 -m venv $VENV_NAME

echo "Activating virtual environment..."
source $VENV_NAME/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "Dependencies installed successfully."
else
    echo "Error: requirements.txt not found."
fi

echo ""
echo "Setup complete!"
echo "To activate the environment, run:"
echo "  source $VENV_NAME/bin/activate"

#!/bin/bash

# Exit script on any error
set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Project setup variables
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_VERSION="python3"

# Check if Python 3 is installed
if ! command -v $PYTHON_VERSION &> /dev/null
then
    echo "Python 3 could not be found. Please install Python 3."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    $PYTHON_VERSION -m venv $VENV_DIR
else
    echo -e "${GREEN}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

# Install required Python packages
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${GREEN}Installing requirements from requirements.txt...${NC}"
    pip install -r "$REQUIREMENTS_FILE"
else
    echo -e "${GREEN}No requirements.txt found. Skipping dependency installation.${NC}"
fi

# Rename .env-template to .env if it exists and .env does not already exist
ENV_TEMPLATE_FILE="$PROJECT_DIR/.env-template"
ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_TEMPLATE_FILE" ]; then
    echo -e "${GREEN}Renaming .env-template to .env...${NC}"
    mv "$ENV_TEMPLATE_FILE" "$ENV_FILE"
else
    echo -e "${GREEN}Either .env already exists or no .env-template file found. Skipping renaming.${NC}"
fi

python3 setup.py sdist
pip install -e .
# Additional setup tasks
# Add any additional setup here, like environment variables or creating necessary directories

# Deactivate virtual environment
deactivate

# Completion message
echo -e "${GREEN}Setup complete!${NC}"

# Instructions for the user
echo -e "${GREEN}To start working on your project, activate the virtual environment by running:${NC}"
echo "source .venv/bin/activate"
#!/bin/bash

# Simple MedAssist AI Pro Demo Runner
echo "🏥 Starting MedAssist AI Pro - Simple Demo"
echo "=========================================="

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing dependencies..."
    pip install -r requirements_simple.txt
fi

# Run the simple app
echo "🚀 Launching app on http://localhost:8502"
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run simple_app.py --server.port 8502

#!/bin/bash
echo "Stopping Flask app..."
pkill -f "python app.py" || true
echo "App stopped"
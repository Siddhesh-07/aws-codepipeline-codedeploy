#!/bin/bash
echo "Starting Flask app..."
cd /home/ubuntu/app
pip install -r requirements.txt
nohup python app.py > /home/ubuntu/app/app.log 2>&1 &
echo "App started"
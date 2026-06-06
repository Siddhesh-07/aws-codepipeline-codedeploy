from flask import Flask, jsonify
import datetime
import socket
import time

app = Flask(__name__)
START_TIME = time.time()

@app.route('/health', methods=['GET'])
def health_check():
    uptime_seconds = int(time.time() - START_TIME)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "host": socket.gethostname(),
        "version": "1.0.0"
    }), 200

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "message": "Health Check API is running",
        "endpoint": "/health"
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
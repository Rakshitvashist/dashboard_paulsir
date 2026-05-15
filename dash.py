from flask import Flask, send_from_directory, jsonify
import os

app = Flask(__name__)

# Serve the main dashboard
@app.route('/')
def index():
    return send_from_directory('.', 'Trading_dashboard.html')

# Serve the data JSON
@app.route('/trader_data.json')
def get_data():
    return send_from_directory('.', 'trader_data.json')

if __name__ == '__main__':
    print("Dashboard Server Starting...")
    print("Access your dashboard at: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)

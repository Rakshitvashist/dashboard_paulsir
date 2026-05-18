from flask import Flask, send_from_directory
import os
import sys

app = Flask(__name__)

@app.route('/')
def index():
    if os.path.exists('dist/index.html'):
        return send_from_directory('dist', 'index.html')
    return send_from_directory('.', 'index_old.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join('dist', path)):
        return send_from_directory('dist', path)
    return send_from_directory('.', path)

@app.route('/trader_data.json')
def get_data():
    return send_from_directory('.', 'trader_data.json')

if __name__ == '__main__':
    # Start the live data processor in a background thread.
    # We check WERKZEUG_RUN_MAIN to ensure we don't start the thread twice when Flask's debug reloader is active.
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        import threading
        from process_trader_data import live_processor_loop
        
        processor_thread = threading.Thread(target=live_processor_loop, daemon=True)
        processor_thread.start()
        print(">>> Background Live Data Processor Thread Started.")

    import socket
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    local_ip = get_local_ip()
    print("Dashboard Server Starting...")
    print(f"Access locally on this PC: http://127.0.0.1:5000")
    print(f"Access on Safari (Mobile/Mac) on same Wi-Fi: http://{local_ip}:5000")
    
    # Run Flask bound to 0.0.0.0 so external devices on the same Wi-Fi can connect
    app.run(debug=True, host='0.0.0.0', port=5000)

import os
import platform
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/ping', methods=['POST'])
def run_ping():
    data = request.get_json()
    if not data or 'server_ips' not in data:
        return jsonify({'error': 'server_ips list is required'}), 400

    server_ips = data.get('server_ips', [])
    ping_param = '-n' if platform.system().lower() == 'windows' else '-c'
    results = []

    for ip in server_ips:
        command = ['ping', ping_param, '1', ip]
        try:
            res = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            is_alive = (res.returncode == 0)
        except subprocess.TimeoutExpired:
            is_alive = False
        except Exception:
            is_alive = False
        
        results.append({'ip': ip, 'alive': is_alive})

    return jsonify({'results': results})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

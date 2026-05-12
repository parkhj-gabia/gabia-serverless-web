#!/bin/bash
# e2-micro 가상머신 부팅 시 자동으로 파이썬 Ping 서버를 세팅하는 스크립트

# 1. 필수 시스템 패키지 설치
apt-get update
apt-get install -y python3-pip python3-venv

# 2. 작업 폴더 생성
mkdir -p /opt/ping-worker
cd /opt/ping-worker

# 3. 파이썬 스크립트 및 요구사항 파일 생성
cat << 'EOF' > worker.py
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
EOF

cat << 'EOF' > requirements.txt
Flask==3.0.3
EOF

# 4. 가상 환경 설정 및 패키지 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. 백그라운드 서비스(systemd) 등록
cat << 'EOF' > /etc/systemd/system/ping-worker.service
[Unit]
Description=Ping Worker API
After=network.target

[Service]
User=root
WorkingDirectory=/opt/ping-worker
Environment="PATH=/opt/ping-worker/venv/bin"
ExecStart=/opt/ping-worker/venv/bin/python worker.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 6. 서비스 실행
systemctl daemon-reload
systemctl enable ping-worker
systemctl start ping-worker

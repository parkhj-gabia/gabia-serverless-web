#!/bin/bash
echo "========================================="
echo " Gabia Serverless Ping Worker Installer & Runner (Linux)"
echo "========================================="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] 에러: Python 3가 설치되어 있지 않습니다."
    echo "    패키지 관리자(apt, yum 등)를 통해 python3를 먼저 설치해 주세요."
    exit 1
fi

# Check Node.js/npm for npx tunnel
HAS_NPX=true
if ! command -v npx &> /dev/null; then
    echo "[*] 알림: Node.js/npm이 설치되어 있지 않습니다."
    echo "    설치하지 않아도 로컬 주소(127.0.0.1)로 연동 가능하지만,"
    echo "    GCP 웹 사이트에서 접속하려면 Node.js를 설치하여 npx 터널을 가동해야 합니다."
    echo "-----------------------------------------"
    HAS_NPX=false
fi

# Install dependencies
echo "[*] 필요한 Python 패키지(Flask)를 설치하는 중..."
python3 -m pip install -r requirements.txt

# Run Python worker and spawn tunnel, forwarding command-line arguments
echo "[*] 워커 및 터널 서비스를 가동합니다..."
if [ "$HAS_NPX" = true ]; then
    # Raw Socket 사용을 위해 Linux에서는 sudo 권한 또는 cap_net_raw 설정 권장
    echo "[*] ICMP Raw Socket 권한 확보를 위해 실행합니다..."
    sudo python3 worker.py --tunnel "$@"
else
    sudo python3 worker.py "$@"
fi

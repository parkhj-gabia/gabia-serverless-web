#!/bin/bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="us-central1"
ZONE="us-central1-a"
VM_NAME="ping-worker-vm"
FUNCTION_NAME="gabia-serverless-web"

echo "========================================="
echo "☁️ 구글 클라우드 자동 배포 스크립트 ☁️"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "========================================="

if [ -z "$PROJECT_ID" ]; then
    echo "[오류] gcloud 프로젝트가 설정되어 있지 않습니다."
    echo "'gcloud config set project [YOUR_PROJECT_ID]' 명령어를 먼저 실행해주세요."
    exit 1
fi

echo -e "\n▶ 1. 필수 API 활성화 중 (수 분이 소요될 수 있습니다)..."
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudbuild.googleapis.com \
    compute.googleapis.com \
    firestore.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com

echo -e "\n▶ 2. 방화벽 규칙 생성 (포트 5000 허용)..."
gcloud compute firewall-rules create allow-ping-worker-5000 \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:5000 \
    --source-ranges=0.0.0.0/0 \
    2>/dev/null || echo "방화벽 규칙이 이미 존재합니다. 넘어갑니다."

echo -e "\n▶ 3. 무료 티어 가상머신(Ping Worker) 생성 중..."
gcloud compute instances create $VM_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --network-interface=network-tier=PREMIUM,subnet=default \
    --metadata-from-file startup-script=vm-startup.sh \
    --tags=ping-worker \
    2>/dev/null || echo "가상머신이 이미 존재합니다. 넘어갑니다."

echo -e "\n▶ 4. 가상머신의 고정 IP 추출 중..."
VM_IP=$(gcloud compute instances describe $VM_NAME \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

if [ -z "$VM_IP" ]; then
    echo "[오류] 가상머신 IP를 가져오지 못했습니다."
    exit 1
fi

echo "✅ Ping Worker VM IP: $VM_IP"
WORKER_API_URL="http://$VM_IP:5000/ping"

echo -e "\n▶ 5. 메인 웹 앱(Cloud Functions) 배포 중..."
echo "이 작업은 약 2~3분 정도 소요됩니다."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=nodejs20 \
    --region=$REGION \
    --source=. \
    --entry-point=app \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars WORKER_API_URL=$WORKER_API_URL

echo -e "\n========================================="
echo "🎉 모든 배포가 완료되었습니다!"
echo "위 로그에서 'url:' 또는 'Service URL:' 항목에 표시된 주소가 웹사이트 접속 주소입니다."
echo "💡 참고: Firestore 데이터베이스 초기화는 구글 클라우드 콘솔에서 직접 수행해야 합니다 (가이드라인 참고)."
echo "========================================="

$ErrorActionPreference = "Continue"

# Configuration
$PROJECT_ID = (gcloud.cmd config get-value project 2>$null)
if ($null -eq $PROJECT_ID) {
    $PROJECT_ID = (gcloud config get-value project 2>$null)
}
$REGION = "us-central1"
$ZONE = "us-central1-a"
$VM_NAME = "ping-worker-vm"
$FUNCTION_NAME = "gabia-serverless-web"

Write-Host "========================================="
Write-Host "☁️ 구글 클라우드 자동 배포 스크립트 (Windows PowerShell) ☁️"
Write-Host "Project ID: $PROJECT_ID"
Write-Host "Region: $REGION"
Write-Host "========================================="

if (-not $PROJECT_ID) {
    Write-Error "[오류] gcloud 프로젝트가 설정되어 있지 않습니다."
    Write-Host "'gcloud config set project [YOUR_PROJECT_ID]' 명령어를 먼저 실행해주세요."
    exit 1
}

Write-Host "`n▶ 1. 필수 API 활성화 중 (수 분이 소요될 수 있습니다)..."
gcloud.cmd services enable `
    cloudfunctions.googleapis.com `
    cloudbuild.googleapis.com `
    compute.googleapis.com `
    firestore.googleapis.com `
    run.googleapis.com `
    artifactregistry.googleapis.com

Write-Host "`n▶ 2. 방화벽 규칙 생성 (포트 5000 허용)..."
gcloud.cmd compute firewall-rules create allow-ping-worker-5000 `
    --direction=INGRESS `
    --priority=1000 `
    --network=default `
    --action=ALLOW `
    --rules=tcp:5000 `
    --source-ranges=0.0.0.0/0 `
    2>$null

Write-Host "`n▶ 3. 무료 티어 가상머신(Ping Worker) 생성 및 업데이트 중..."
$vmCheck = gcloud.cmd compute instances describe $VM_NAME --zone=$ZONE --project=$PROJECT_ID 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "가상머신이 이미 존재합니다. 스타트업 스크립트 메타데이터를 업데이트합니다..."
    gcloud.cmd compute instances add-metadata $VM_NAME `
        --project=$PROJECT_ID `
        --zone=$ZONE `
        --metadata-from-file startup-script=vm-startup.sh
    Write-Host "가상머신을 재부팅하여 새 설정을 적용합니다 (약 30초 소요)..."
    gcloud.cmd compute instances reset $VM_NAME `
        --project=$PROJECT_ID `
        --zone=$ZONE
} else {
    Write-Host "가상머신을 새로 생성합니다..."
    gcloud.cmd compute instances create $VM_NAME `
        --project=$PROJECT_ID `
        --zone=$ZONE `
        --machine-type=e2-micro `
        --network-interface=network-tier=PREMIUM,subnet=default `
        --metadata-from-file startup-script=vm-startup.sh `
        --tags=ping-worker
}

Write-Host "`n▶ 4. 가상머신의 고정 IP 추출 중..."
$VM_IP = (gcloud.cmd compute instances describe $VM_NAME `
    --zone=$ZONE `
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

if (-not $VM_IP) {
    Write-Error "[오류] 가상머신 IP를 가져오지 못했습니다."
    exit 1
}

Write-Host "✅ Ping Worker VM IP: $VM_IP"
$WORKER_API_URL = "http://$($VM_IP):5000/ping"

Write-Host "`n▶ 5. 메인 웹 앱(Cloud Functions) 배포 중..."
Write-Host "이 작업은 약 2~3분 정도 소요됩니다."
gcloud.cmd functions deploy $FUNCTION_NAME `
    --gen2 `
    --runtime=nodejs20 `
    --region=$REGION `
    --source=. `
    --entry-point=app `
    --trigger-http `
    --allow-unauthenticated `
    --set-env-vars WORKER_API_URL=$WORKER_API_URL

Write-Host "`n========================================="
Write-Host "🎉 모든 배포가 완료되었습니다!"
Write-Host "========================================="

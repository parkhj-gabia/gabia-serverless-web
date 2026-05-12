# L2 핑 점검 대시보드 (Gabia Serverless Web)

서버리스(Cloud Functions)와 가상머신(e2-micro)의 장점을 결합한 하이브리드 아키텍처 기반의 **L2 스위치 및 하위 서버 핑(Ping) 점검 웹 대시보드**입니다.

## 🚀 아키텍처 구성
* **메인 웹 서버**: Node.js 기반 (Google Cloud Functions 구동)
* **Ping Worker**: Python Flask API (무료 티어 e2-micro VM 구동, ICMP Ping 실행)
* **데이터베이스**: Firestore (L2 점검 대상 IP 리스트 동기화 및 관리)

## 🌐 웹페이지 호출 방법 및 테스트

현재 구글 클라우드에 전체 공개(Public)로 배포되어 있어 어디서든 브라우저를 통해 접속할 수 있습니다.

**접속 URL:**
👉 [https://us-central1-gabia-serverless-app.cloudfunctions.net/gabia-serverless-web/](https://us-central1-gabia-serverless-app.cloudfunctions.net/gabia-serverless-web/)

*(주의: 접속 시 URL 맨 끝에 슬래시(`/`)가 포함되어야 화면 스타일(CSS)이 정상적으로 로드됩니다.)*

### 🛠️ 사용 방법
1. 위 URL로 접속하여 왼쪽 메뉴에서 **[L2 핑 점검]**을 선택합니다.
2. 입력창에 점검할 **IP 주소**를 직접 입력하거나, **장애 알람 텍스트** 전체를 복사하여 붙여넣습니다. 
   *(시스템이 정규식을 이용해 텍스트 내에서 IP를 자동으로 추출합니다.)*
3. **[점검 실행]** 버튼을 누릅니다.
4. 클라우드에 띄워진 파이썬 워커(Worker) 서버가 해당 L2 스위치의 하위 서버들에게 1초간 ICMP 핑을 날리고, 그 결과를 화면에 반환합니다.

### 📝 설정 리스트 관리 (`l2.list`)
* 화면 하단의 **[L2 리스트 수정하기]** 버튼을 클릭하면, 점검의 기준이 되는 서버 트리 리스트를 웹에서 직접 편집하고 Firestore DB에 영구적으로 저장할 수 있습니다.

---

## 💻 개발자용 (로컬 실행 방법)

개발 환경에서 테스트하기 위해서는 메인 서버와 워커 서버를 모두 실행해야 합니다.

```bash
# 1. 패키지 설치
npm install
cd App.L2 && pip install -r requirements.txt && cd ..

# 2. 터미널 1: Python Ping Worker 실행 (포트 5000)
python3 App.L2/worker.py

# 3. 터미널 2: Node.js 메인 서버 실행 (포트 8080)
npm start
```
이후 `http://localhost:8080` 으로 접속합니다.

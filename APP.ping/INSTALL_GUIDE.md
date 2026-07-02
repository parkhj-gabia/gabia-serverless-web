# APP.ping 워커(Worker) 설치 및 실행 가이드

이 문서는 `worker.py` 서버를 임의의 환경(Windows, Linux, macOS)에서 단독으로 설치하고 안전하게 실행할 수 있는 절차를 한국어로 상세히 안내합니다.

---

## 📌 주요 사전 정보 (필독)

*   **워커의 역할**: 브라우저(대시보드)로부터 검사 대상 IP 리스트를 전달받아, 서버 내부에서 비동기 병렬 핑을 수행한 후 결과를 JSON 형식으로 반환합니다.
*   **권한 요구사항**: 파이썬의 로우 소켓(Raw Socket) 기반 ICMP 핑을 전송하려면 **운영체제의 관리자(루트) 권한**이 반드시 필요합니다.
    *   **관리자 권한으로 실행 시**: 로우 소켓(`socket.SOCK_RAW`)을 직접 통제하여 오버헤드 없는 정확한 핑 수집 가능.
    *   **일반 권한으로 실행 시**: 권한 오류(`PermissionError`) 감지 후 자동으로 OS 시스템 `ping` 명령어(CLI) 실행 또는 TCP(`80`/`443`) 포트 접속 시도로 우회 작동(Fallback).

---

## 🖥️ 환경별 설치 및 실행 순서

### 1단계. 파이썬(Python) 설치 확인

시스템에 파이썬 3.8 이상이 설치되어 있는지 확인합니다.

*   **Windows**:
    1. [공식 홈페이지](https://www.python.org/downloads/)에서 최신 3.x 버전 인스톨러 다운로드.
    2. 설치 시 반드시 **"Add Python to PATH"** (환경 변수 등록) 체크박스를 선택한 후 설치 진행.
*   **Linux (Ubuntu/Debian)**:
    ```bash
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
    ```
*   **macOS**:
    ```bash
    brew install python
    ```

---

### 2단계. 가상환경 세팅 및 패키지 설치

워커 서버 파일이 위치한 폴더(`APP.ping/`)로 이동하여 독립된 라이브러리 환경을 구축합니다.

#### 1. 터미널/명령 프롬프트 열기 후 폴더 이동
```bash
cd APP.ping
```

#### 2. 가상환경(venv) 생성
```bash
python -m venv venv
```
*(Windows 환경에서 `python` 명령어가 작동하지 않는다면 `python3 -m venv venv` 또는 `py -m venv venv`로 시도합니다.)*

#### 3. 가상환경 활성화
*   **Windows (Command Prompt / cmd)**:
    ```cmd
    venv\Scripts\activate
    ```
*   **Windows (PowerShell)**:
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```
    *(보안 오류 발생 시 PowerShell을 관리자 권한으로 열어 `Set-ExecutionPolicy RemoteSigned` 명령을 먼저 실행해야 합니다.)*
*   **Linux / macOS**:
    ```bash
    source venv/bin/activate
    ```

#### 4. 필수 의존성 패키지 설치
가상환경이 활성화된 상태(`(venv)` 표시 확인)에서 실행합니다.
```bash
pip install -r requirements.txt
```

---

### 3단계. 관리자 권한으로 서버 기동 (핵심)

로우 소켓 사용을 위해 터미널을 **반드시 권한을 상승시켜 실행**해야 합니다.

#### 1) Windows 환경 (관리자 모드 실행)
1. 시작 메뉴에서 **"명령 프롬프트(cmd)"** 검색.
2. 마우스 우클릭 후 **"관리자 권한으로 실행"** 선택.
3. 해당 관리자 터미널에서 작업 폴더로 이동 후 가상환경의 파이썬을 지정해 실행합니다.
   ```cmd
   cd C:\path\to\gabia-serverless-web\APP.ping
   venv\Scripts\python worker.py --port 9000 --host 0.0.0.0
   ```
   *(포트 번호는 `--port` 옵션으로 변경 가능합니다. 기본값은 5000)*

#### 2) Linux / macOS 환경
`sudo` 명령어를 활용하여 가상환경 내의 파이썬 실행 파일을 직접 구동합니다.
```bash
sudo venv/bin/python worker.py --port 9000 --host 0.0.0.0
```

---

## 🔍 정상 작동 여부 확인 방법 (자가 진단)

서버를 띄운 상태에서 브라우저 또는 API 테스트 도구(Postman, curl 등)를 이용해 연결과 권한을 확인합니다.

### 1. 웹 브라우저에서 상태 API 호출
브라우저 주소창에 `http://<실행서버IP>:9000/status`를 입력합니다.
*   **응답 예시 (성공 및 로우 소켓 권한 획득)**:
    ```json
    {
      "has_raw_privilege": true,
      "platform": "Windows",
      "status": "online"
    }
    ```
*   만약 `"has_raw_privilege": false`로 뜬다면 관리자 권한 상승이 정상적으로 되지 않은 상태이므로 실행 절차를 다시 확인해야 합니다. (이 상태에서도 일반 핑 명령어 기반 우회 모드로 서비스 작동은 지속됩니다.)

### 2. 방화벽 설정 확인
원격 서버나 외부 PC에서 이 워커에 접속하여 핑 대상을 점검하려는 경우, 실행한 포트(예: TCP `9000`번)가 운영체제 방화벽(Windows 고급 보안 방화벽, Linux ufw 등) 및 클라우드(GCP 방화벽 규칙)에서 **인바운드 허용(ALLOW)**되어 있는지 확인해야 합니다.

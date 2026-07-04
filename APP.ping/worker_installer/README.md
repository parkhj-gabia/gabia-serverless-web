# Gabia Serverless Ping Worker Installer Package

본 폴더는 각 지점(OS: Windows / macOS / Linux)에 설치하여 비동기 대용량 핑을 수행하는 분산 워커 설치 패키지입니다.

## 파일 구성
* `worker.py`: 핑 점검 및 API 서빙 스크립트 (Flask 기반, 자동 npx 터널링 포함)
* `requirements.txt`: Python 의존성 목록
* `run_mac.sh`: macOS 전용 간편 원클릭 실행 스크립트
* `run_linux.sh`: Linux 전용 간편 실행 스크립트
* `run_windows.bat`: Windows 전용 간편 실행 스크립트

## 실행 및 설치 방법

### 1. 전제 조건
* **Python 3**: 시스템에 파이썬이 설치되어 있어야 합니다.
* **Node.js** (선택 권장): 워커를 공용 웹 브라우저(GCP 웹사이트) 환경과 자동 연동하기 위해 **npx** 터널링 프로그램 설치용 Node.js 설치를 강력히 권장합니다.

### 2. 실행
사용하시는 OS에 맞게 스크립트를 실행해 주세요.
* **macOS / Linux**:
  ```bash
  chmod +x run_mac.sh
  ./run_mac.sh
  ```
* **Windows**: `run_windows.bat`를 더블클릭하여 실행합니다.

### 3. 커스텀 포트 설정 옵션
기본 포트(5000)가 아닌 다른 포트로 실행하려면 뒤에 `--port` 옵션을 추가해 줍니다:
* **macOS / Linux**:
  ```bash
  ./run_mac.sh --port 6000
  ```
* **Windows**: 명령 프롬프트(CMD) 창에서 다음과 같이 실행합니다:
  ```cmd
  run_windows.bat --port 6000
  ```

실행 후 터미널에 아래와 같은 로그가 나타납니다:
```
🎉 터널 생성 완료: https://xxxx.localtunnel.me
```

이 주소(`https://xxxx.localtunnel.me`)가 자동으로 대시보드 웹 브라우저 화면에 수집되거나, 복사하여 수동으로 워커 설정 화면에 기입하시면 됩니다.

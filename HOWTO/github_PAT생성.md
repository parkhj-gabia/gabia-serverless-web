# GitHub Personal Access Token (PAT) 생성 및 등록 가이드

이 문서에서는 L2/IP 점검 대시보드의 백업 기능을 수행하기 위해 안전하게 GitHub Personal Access Token(PAT)을 생성하고 Firestore에 저장하는 절차를 설명합니다.

보안을 위해 계정 전체에 권한을 주는 Classic 토큰 대신, **지정한 저장소에만 쓰기 권한을 부여할 수 있는 Fine-grained 토큰(세립형 토큰)** 방식으로 생성해야 합니다.

---

## 1단계. GitHub에서 Fine-grained PAT 생성

1. **GitHub 접속 및 설정 이동:**
   * GitHub에 로그인한 후, 우측 상단 프로필 이미지 클릭 ➡️ **Settings** 선택.
   * 왼쪽 사이드바 맨 하단의 **Developer Settings** 클릭.
   * **Personal access tokens** ➡️ **Fine-grained tokens** 클릭.
   * 우측 상단의 **Generate new token** 클릭.

2. **기본 정보 입력:**
   * **Token name**: 토큰 이름 설정 (예: `gabia-dashboard-backup-token`)
   * **Expiration**: 토큰 유효 기간 설정 (보안을 위해 90일 이하 권장)
   * **Description**: 토큰 설명 작성 (예: `L2 & IP Check List Backup to Cloud`)

3. **저장소 접근 범위 설정 (Repository access):**
   * **"Only select repositories"** 옵션을 선택합니다.
   * 저장소 목록 드롭다운에서 **`gabia-serverless-web`** 저장소만 지정하여 선택합니다.
   * *(이를 통해 토큰이 탈취되더라도 타 프라이빗 저장소에 대한 접근을 완벽히 차단합니다.)*

4. **저장소 권한 설정 (Permissions):**
   * **Repository permissions** 목록을 확장합니다.
   * **`Contents`** 항목을 찾아 Access 권한을 **`Read and write`**로 변경합니다.
   * *(백업 목록을 원격 리포지토리에 커밋 및 push하기 위해 꼭 필요한 유일한 권한입니다.)*
   * 나머지 모든 권한은 **No access** 상태로 둡니다.

5. **생성 완료:**
   * 페이지 맨 하단의 **Generate token**을 클릭합니다.
   * 생성된 토큰 값(`github_pat_...`)은 창을 닫으면 다시 볼 수 없으므로 **안전한 곳에 복사**해 둡니다.

---

## 2단계. Firestore에 토큰 등록하기

서버가 런타임에 동적으로 토큰을 조회하여 백업 작업을 수행할 수 있도록 Firestore에 저장해야 합니다.

### 방법 A. 제공된 로컬 스크립트로 등록 (권장)
설치된 의존성을 활용해 터미널 명령어 한 줄로 편리하게 등록할 수 있습니다. 

*보안을 위해 명령어 **맨 앞에 공백(스페이스바 한 칸)**을 입력하여 터미널 히스토리에 토큰 값이 남지 않도록 합니다.*

```bash
# 명령어 맨 앞에 스페이스바 한 칸을 띄운 뒤 실행해주세요.
 node set-github-token.js <복사한_GITHUB_TOKEN>
```
*성공 메시지: `✅ 성공적으로 Firestore의 'config/github' 문서에 토큰을 저장했습니다!`*

### 방법 B. GCP Firestore Console에서 수동 등록
1. [구글 클라우드 콘솔 Firestore](https://console.cloud.google.com/firestore/) 페이지에 로그인합니다.
2. `config` 컬렉션을 생성합니다. (이미 있으면 선택)
3. 문서 ID를 `github`로 지정하여 새 문서를 만듭니다.
4. 문서 내에 아래 필드를 설정합니다:
   * **필드 이름**: `token`
   * **유형**: `string`
   * **값**: 복사한 GitHub Token (`github_pat_...`)

---

## ⚠️ 보안 및 관리 가이드라인

* **터미널 명령어 이력 지우기**: 만약 실수로 공백 없이 명령어를 입력하셨다면, 터미널에 `history -c`를 입력하거나 `~/.zsh_history` 파일을 열어 해당 라인을 제거해 주세요.
* **토큰 유출 시 대응**: 만약 생성한 토큰이 유출되었다고 의심된다면, 즉시 GitHub **Developer Settings ➡️ Fine-grained tokens** 목록에서 해당 토큰을 찾아 **Revoke** 또는 **Delete** 버튼을 클릭하여 파기해 주세요.
* **만료일 갱신**: 토큰 만료일이 도래하면 GitHub에서 자동으로 안내 이메일이 발송됩니다. 해당 토큰 페이지에서 **Regenerate**를 실행하여 신규 토큰을 발급받은 뒤, 위의 2단계 과정을 통해 Firestore 값을 갱신해 주시면 서비스 중단 없이 유지됩니다.

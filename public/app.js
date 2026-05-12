// Mock data for applications
const apps = [
    {
        id: 'app1',
        title: 'App.L2 점검',
        icon: '🖧',
        description: 'L2 스위치 및 하위 서버 상태 점검',
        content: `
            <div class="app-card">
                <h3>L2 서버 점검 실행</h3>
                <p style="color: var(--text-secondary); margin-top: 8px;">점검할 L2 스위치의 IP를 입력하고 실행 버튼을 눌러주세요.</p>
                <div style="display: flex; gap: 12px; margin-top: 16px;">
                    <textarea id="l2IpInput" placeholder="IP 주소 또는 장애 내용 텍스트를 붙여넣으세요..." style="flex: 1; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-color); color: var(--text-primary); outline: none; font-size: 1rem; resize: vertical; min-height: 48px; max-height: 200px;" rows="2"></textarea>
                    <button class="btn btn-primary" id="runL2Btn" style="padding: 0 24px; height: fit-content; align-self: center;">점검 실행</button>
                </div>
            </div>
            <div class="app-card" style="margin-top: 16px; position: relative;">
                <h3>실행 결과</h3>
                <div id="l2Loading" style="display: none; position: absolute; top: 24px; right: 24px; color: var(--accent-color);">실행 중...</div>
                <pre id="l2Output" style="margin-top: 16px; background: #000; padding: 16px; border-radius: 8px; color: #a3ffa3; font-family: monospace; font-size: 0.9rem; min-height: 150px; overflow-x: auto; white-space: pre-wrap;">실행 결과가 여기에 표시됩니다.</pre>
            </div>
            <div class="app-card" style="margin-top: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3>l2.list 설정 관리</h3>
                        <p style="color: var(--text-secondary); margin-top: 4px; font-size: 0.9rem;">점검 대상 서버 목록(l2.list)을 새 창에서 수정합니다.</p>
                    </div>
                    <button class="btn" id="openL2ListModalBtn" style="background: var(--surface-hover); color: var(--text-primary);">L2 리스트 수정하기</button>
                </div>
            </div>
        `
    },
    {
        id: 'app2',
        title: 'App 2',
        icon: '⚙️',
        description: '서비스 환경 설정 및 관리 도구',
        content: `
            <div class="app-card">
                <h3>서비스 설정</h3>
                <div style="margin-top: 16px; display: flex; flex-direction: column; gap: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.02); border-radius: 8px;">
                        <div>
                            <strong>자동 스케일링</strong>
                            <div style="font-size: 12px; color: var(--text-secondary);">트래픽 증가 시 자동으로 리소스 확장</div>
                        </div>
                        <div style="width: 40px; height: 20px; background: var(--accent-color); border-radius: 10px; position: relative; cursor: pointer;">
                            <div style="position: absolute; right: 2px; top: 2px; width: 16px; height: 16px; background: white; border-radius: 50%;"></div>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.02); border-radius: 8px;">
                        <div>
                            <strong>디버그 모드</strong>
                            <div style="font-size: 12px; color: var(--text-secondary);">상세한 로그 기록 활성화</div>
                        </div>
                        <div style="width: 40px; height: 20px; background: var(--surface-hover); border-radius: 10px; position: relative; cursor: pointer;">
                            <div style="position: absolute; left: 2px; top: 2px; width: 16px; height: 16px; background: white; border-radius: 50%;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `
    },
    {
        id: 'app3',
        title: 'App 3',
        icon: '📁',
        description: '데이터베이스 및 스토리지 관리',
        content: `
            <div class="app-card">
                <h3>스토리지 사용량</h3>
                <div style="margin-top: 16px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>용량</span>
                        <span>45GB / 100GB</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: var(--surface-hover); border-radius: 4px; overflow: hidden;">
                        <div style="width: 45%; height: 100%; background: var(--accent-color);"></div>
                    </div>
                </div>
            </div>
            <div class="app-card" style="margin-top: 16px;">
                <button class="btn btn-primary">데이터베이스 백업 실행</button>
            </div>
        `
    }
];

document.addEventListener('DOMContentLoaded', () => {
    const appList = document.getElementById('appList');
    const appContent = document.getElementById('appContent');
    const loginBtn = document.getElementById('loginBtn');

    // Initialize sidebar
    function initSidebar() {
        apps.forEach(app => {
            const li = document.createElement('li');
            li.className = 'app-item';
            li.dataset.id = app.id;
            li.innerHTML = `
                <span class="app-icon">${app.icon}</span>
                <span class="app-name">${app.title}</span>
            `;
            
            li.addEventListener('click', () => selectApp(app.id));
            appList.appendChild(li);
        });
    }

    // Handle app selection
    function selectApp(appId) {
        // Update active state in sidebar
        document.querySelectorAll('.app-item').forEach(item => {
            if (item.dataset.id === appId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Find app data
        const app = apps.find(a => a.id === appId);
        if (!app) return;

        // Render content
        renderContent(app);
    }

    // Render app content
    function renderContent(app) {
        // Remove animation to re-trigger it
        appContent.style.animation = 'none';
        appContent.offsetHeight; // trigger reflow
        appContent.style.animation = null;

        appContent.innerHTML = `
            <div class="app-header">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 2rem;">${app.icon}</span>
                    <div>
                        <h2>${app.title}</h2>
                        <p>${app.description}</p>
                    </div>
                </div>
            </div>
            <div class="app-body">
                ${app.content}
            </div>
        `;

        if (app.id === 'app1') {
            const runBtn = document.getElementById('runL2Btn');
            const ipInput = document.getElementById('l2IpInput');
            const outputBlock = document.getElementById('l2Output');
            const loadingIndicator = document.getElementById('l2Loading');

            if (runBtn) {
                runBtn.addEventListener('click', async () => {
                    const rawText = ipInput.value.trim();
                    if (!rawText) {
                        outputBlock.innerText = "IP 주소 또는 장애 텍스트를 입력해주세요.";
                        return;
                    }
                    
                    let ip = rawText;
                    // Regex로 첫 번째 IP 추출
                    const ipMatch = rawText.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/);
                    if (ipMatch) {
                        ip = ipMatch[0];
                        ipInput.value = ip; // 텍스트를 추출한 IP로 정리해 줌
                    } else {
                        outputBlock.innerText = "입력하신 텍스트에서 IP 주소를 찾을 수 없습니다.";
                        return;
                    }

                    runBtn.disabled = true;
                    loadingIndicator.style.display = 'block';
                    outputBlock.innerText = "서버 상태 확인 중...";

                    try {
                        const response = await fetch('/api/run-l2', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ip })
                        });
                        
                        const result = await response.json();
                        outputBlock.innerText = result.output || result.error || "결과 없음";
                    } catch (err) {
                        outputBlock.innerText = "실행 중 오류가 발생했습니다: " + err.message;
                    } finally {
                        runBtn.disabled = false;
                        loadingIndicator.style.display = 'none';
                    }
                });
            }

            const openModalBtn = document.getElementById('openL2ListModalBtn');
            if (openModalBtn) {
                openModalBtn.addEventListener('click', window.openL2Modal);
            }
        }
    }

    // Dummy Login Action
    loginBtn.addEventListener('click', () => {
        if(loginBtn.innerText === '로그인') {
            loginBtn.innerText = '로그아웃';
            loginBtn.style.backgroundColor = 'var(--surface-hover)';
            loginBtn.style.color = 'var(--text-primary)';
        } else {
            loginBtn.innerText = '로그인';
            loginBtn.style.backgroundColor = 'var(--accent-color)';
            loginBtn.style.color = 'white';
        }
    });

    // Modal Logic
    const l2Modal = document.getElementById('l2ListModal');
    const closeL2ModalBtn = document.getElementById('closeL2ListModal');
    const saveL2Btn = document.getElementById('saveL2ListBtn');
    const l2Editor = document.getElementById('l2ListEditor');
    const saveL2Status = document.getElementById('l2ListSaveStatus');

    if (closeL2ModalBtn) {
        closeL2ModalBtn.addEventListener('click', () => {
            l2Modal.classList.remove('active');
        });
    }

    if (saveL2Btn) {
        saveL2Btn.addEventListener('click', async () => {
            const content = l2Editor.value;
            saveL2Btn.disabled = true;
            saveL2Status.innerText = "저장 중...";
            saveL2Status.style.color = 'var(--text-secondary)';

            try {
                const response = await fetch('/api/l2-list', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content })
                });
                const result = await response.json();
                
                if (result.success) {
                    saveL2Status.innerText = "저장되었습니다.";
                    saveL2Status.style.color = '#10b981';
                } else {
                    saveL2Status.innerText = "저장 실패: " + (result.error || 'Unknown error');
                    saveL2Status.style.color = '#ef4444';
                }
            } catch (err) {
                saveL2Status.innerText = "오류 발생: " + err.message;
                saveL2Status.style.color = '#ef4444';
            } finally {
                saveL2Btn.disabled = false;
                setTimeout(() => {
                    if (saveL2Status.innerText === "저장되었습니다.") saveL2Status.innerText = "";
                }, 3000);
            }
        });
    }

    window.openL2Modal = function() {
        if (!l2Modal) return;
        
        l2Editor.value = "로딩 중...";
        saveL2Status.innerText = "";
        l2Modal.classList.add('active');

        fetch('/api/l2-list')
            .then(res => res.json())
            .then(data => {
                if (data.content !== undefined) {
                    l2Editor.value = data.content;
                } else if (data.error) {
                    l2Editor.value = "Error loading list: " + data.error;
                }
            })
            .catch(err => {
                l2Editor.value = "Error: " + err.message;
            });
    };

    // Start
    initSidebar();
});

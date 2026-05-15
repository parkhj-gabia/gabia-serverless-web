const express = require('express');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const admin = require('firebase-admin');

const app = express();
app.use(express.json());

// Firebase Admin 초기화 (Firestore 연동)
let useFirestore = false;
let db = null;
try {
    // 환경변수에 구글 크레덴셜이 있거나 로컬 ADC(Application Default Credentials)가 잡히면 동작합니다.
    // 구글 클라우드 환경(Cloud Functions)에서는 기본적으로 인증이 자동으로 됩니다.
    admin.initializeApp();
    db = admin.firestore();
    useFirestore = true;
    console.log("Firestore initialized successfully.");
} catch (e) {
    console.log("Firestore initialization failed. Falling back to local file system for l2.list.");
    // 인증 정보가 없어 실패한 경우, verifyIdToken을 정상적으로 수행하기 위해 명시적 프로젝트 ID로 초기화
    try {
        admin.initializeApp({ projectId: 'gabia-serverless-app' });
        console.log("Firebase Admin initialized for token verification only.");
    } catch (initErr) {
        console.log("Token verification initialization failed:", initErr.message);
    }
}

// Cloud Functions 등에서 서브경로로 접속 시 슬래시(/) 누락으로 인한 CSS 경로 깨짐 방지
app.use((req, res, next) => {
    if (req.path === '/' && req.originalUrl && !req.originalUrl.endsWith('/')) {
        return res.redirect(301, req.originalUrl + '/');
    }
    next();
});

app.use(express.static(path.join(__dirname, 'public')));
app.use('/App.buildpassword', express.static(path.join(__dirname, 'App.buildpassword')));
app.use('/APP.ipcheck', express.static(path.join(__dirname, 'APP.ipcheck')));

// L2.list 파싱 유틸리티 함수
function parseL2List(content, targetIp) {
    const lines = content.split('\n');
    let isFound = false;
    let l2Comment = '';
    let serverIps = [];

    for (let line of lines) {
        line = line.trim();
        if (!line) continue;
        
        let cleanLine = line.split('#')[0].trim();
        let comment = line.includes('#') ? line.split('#')[1].trim() : '';

        if (!isFound) {
            if (cleanLine === targetIp) {
                isFound = true;
                l2Comment = comment;
            }
        } else {
            if (cleanLine.startsWith('-')) {
                let ip = cleanLine.substring(1).trim();
                serverIps.push(ip);
            } else {
                break;
            }
        }
    }
    return { isFound, l2Comment, serverIps };
}

// 인증 미들웨어
const authenticateUser = async (req, res, next) => {
    // 로컬 테스트나 Firebase Admin 초기화 실패 시 임시 통과 허용 (선택 사항이나, 클라우드에서는 강제)
    if (!useFirestore) {
        // return next(); // 주석 해제 시 로컬 개발 중에는 인증을 무시합니다.
    }

    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: '인증 토큰이 없습니다.' });
    }

    const idToken = authHeader.split('Bearer ')[1];
    try {
        const decodedToken = await admin.auth().verifyIdToken(idToken);
        req.user = decodedToken;
        
        // 여기에 특정 이메일만 허용하는 로직을 추가할 수 있습니다.
        // const allowedEmails = ['parkhj@gabia.com'];
        // if (!allowedEmails.includes(req.user.email)) {
        //     return res.status(403).json({ error: '접근이 허가되지 않은 계정입니다.' });
        // }
        
        next();
    } catch (err) {
        return res.status(401).json({ error: '유효하지 않은 인증 토큰입니다.', details: err.message });
    }
};

// API Endpoint for App.L2 ping check
app.post('/api/run-l2', authenticateUser, async (req, res) => {
    const { ip } = req.body;
    if (!ip) {
        return res.status(400).json({ error: 'IP address is required' });
    }

    try {
        let content = '';
        if (useFirestore) {
            const doc = await db.collection('config').doc('l2list').get();
            if (doc.exists) {
                content = doc.data().content || '';
            }
        } else {
            const listFilePath = path.join(__dirname, 'App.L2', 'l2.list');
            if (fs.existsSync(listFilePath)) {
                content = fs.readFileSync(listFilePath, 'utf-8');
            }
        }

        const { isFound, l2Comment, serverIps } = parseL2List(content, ip);
        
        if (!isFound) {
            return res.json({ output: `[Error] Cannot find IP ${ip} in the list.` });
        }

        // Ping Worker VM API 호출 (실제 배포 시 환경변수로 VM IP를 지정합니다)
        const workerUrl = process.env.WORKER_API_URL || 'http://127.0.0.1:5000/ping';
        
        try {
            const response = await axios.post(workerUrl, { server_ips: serverIps });
            const results = response.data.results || [];
            
            let headerText = `L2 IP [${ip}]`;
            if (l2Comment) headerText += ` (# ${l2Comment})`;
            headerText += " Sub-server Ping Test Results";

            let outputText = headerText + '\n';
            outputText += '-'.repeat(50) + '\n';
            
            let allAlive = results.length > 0;
            for (let r of results) {
                if (r.alive) {
                    outputText += ` [OK] Alive : ${r.ip}\n`;
                } else {
                    outputText += ` [XX] Dead  : ${r.ip}\n`;
                    allAlive = false;
                }
            }
            outputText += '-'.repeat(50) + '\n';

            res.json({ output: outputText, allAlive });
        } catch (workerErr) {
            res.json({ output: `[Error] Ping Worker VM API Failed.\nURL: ${workerUrl}\nMessage: ${workerErr.message}\nMake sure the worker.py is running.` });
        }
    } catch (err) {
        res.json({ output: `[System Error] ${err.message}` });
    }
});

// l2.list 내용 조회 API
app.get('/api/l2-list', authenticateUser, async (req, res) => {
    try {
        if (useFirestore) {
            const doc = await db.collection('config').doc('l2list').get();
            const content = doc.exists ? (doc.data().content || '') : '';
            return res.json({ content });
        } else {
            const listFilePath = path.join(__dirname, 'App.L2', 'l2.list');
            if (!fs.existsSync(listFilePath)) return res.json({ content: '' });
            const content = fs.readFileSync(listFilePath, 'utf-8');
            return res.json({ content });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// l2.list 내용 저장 API
app.post('/api/l2-list', authenticateUser, async (req, res) => {
    const { content } = req.body;
    if (typeof content !== 'string') return res.status(400).json({ error: 'Invalid content' });

    try {
        if (useFirestore) {
            await db.collection('config').doc('l2list').set({ content });
            return res.json({ success: true });
        } else {
            const listFilePath = path.join(__dirname, 'App.L2', 'l2.list');
            fs.writeFileSync(listFilePath, content, 'utf-8');
            return res.json({ success: true });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// 접속 기록 저장 API
app.post('/api/log-login', authenticateUser, async (req, res) => {
    if (!useFirestore) return res.json({ success: true, note: 'Firestore disabled' });

    try {
        const email = req.user.email || 'Unknown';
        // 클라우드 환경에서는 x-forwarded-for 헤더를 통해 실제 IP를 가져옵니다.
        const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'Unknown IP';
        const userAgent = req.headers['user-agent'] || 'Unknown';
        const timestamp = admin.firestore.FieldValue.serverTimestamp();

        const logsRef = db.collection('login_logs');
        await logsRef.add({
            email,
            ip,
            userAgent,
            timestamp,
            createdAt: new Date().toISOString()
        });

        // 1000개 초과 시 오래된 기록 삭제
        const snapshot = await logsRef.count().get();
        const count = snapshot.data().count;

        if (count > 1000) {
            const excess = count - 1000;
            const oldestDocs = await logsRef.orderBy('createdAt', 'asc').limit(excess).get();
            const batch = db.batch();
            oldestDocs.forEach(doc => {
                batch.delete(doc.ref);
            });
            await batch.commit();
        }

        res.json({ success: true });
    } catch (err) {
        console.error("Login logging error:", err);
        res.status(500).json({ error: err.message });
    }
});

// 접속 기록 조회 API
app.get('/api/login-logs', authenticateUser, async (req, res) => {
    if (!useFirestore) return res.json({ logs: [] });

    try {
        // 최근 100개만 조회 (UI 성능 및 데이터 보호)
        const snapshot = await db.collection('login_logs')
            .orderBy('createdAt', 'desc')
            .limit(100)
            .get();
        
        const logs = [];
        snapshot.forEach(doc => {
            logs.push({ id: doc.id, ...doc.data() });
        });

        res.json({ logs });
    } catch (err) {
        console.error("Fetch login logs error:", err);
        res.status(500).json({ error: err.message });
    }
});

// ipcheck.list 내용 조회 API
app.get('/api/ipcheck-list', authenticateUser, async (req, res) => {
    try {
        let content = '';
        if (useFirestore) {
            const doc = await db.collection('config').doc('ipchecklist').get();
            content = doc.exists ? (doc.data().content || '') : '';
        }
        
        if (!content) {
            const listFilePath = path.join(__dirname, 'APP.ipcheck', 'ipcheck.list');
            if (fs.existsSync(listFilePath)) {
                content = fs.readFileSync(listFilePath, 'utf-8');
            }
        }
        
        return res.json({ content });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// ipcheck.list 내용 저장 API
app.post('/api/ipcheck-list', authenticateUser, async (req, res) => {
    const { content } = req.body;
    if (typeof content !== 'string') return res.status(400).json({ error: 'Invalid content' });

    try {
        if (useFirestore) {
            await db.collection('config').doc('ipchecklist').set({ content });
            return res.json({ success: true });
        } else {
            const listFilePath = path.join(__dirname, 'APP.ipcheck', 'ipcheck.list');
            fs.writeFileSync(listFilePath, content, 'utf-8');
            return res.json({ success: true });
        }
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// IP 조회 API
app.post('/api/check-ip', authenticateUser, async (req, res) => {
    const { ip } = req.body;
    if (!ip) return res.status(400).json({ error: 'IP is required' });

    try {
        let content = '';
        if (useFirestore) {
            const doc = await db.collection('config').doc('ipchecklist').get();
            content = doc.exists ? (doc.data().content || '') : '';
        }
        
        if (!content) {
            const listFilePath = path.join(__dirname, 'APP.ipcheck', 'ipcheck.list');
            if (fs.existsSync(listFilePath)) {
                content = fs.readFileSync(listFilePath, 'utf-8');
            }
        }

        const lines = content.split('\n');
        let foundComment = null;
        let matchedIp = null;

        for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine || trimmedLine.startsWith('###')) continue;
            if (!trimmedLine.includes('#')) continue;

            const parts = trimmedLine.split('#', 2);
            const listIp = parts[0].trim();
            const comment = parts[1].trim();

            if (listIp === ip) {
                matchedIp = listIp;
                foundComment = comment;
                break;
            }

            if (listIp.endsWith('.*')) {
                const prefix = listIp.substring(0, listIp.length - 1); // e.g., '182.162.100.'
                if (ip.startsWith(prefix)) {
                    matchedIp = listIp;
                    foundComment = comment;
                    break;
                }
            }
        }

        if (foundComment) {
            return res.json({ success: true, ip: matchedIp, comment: foundComment });
        } else {
            return res.json({ success: false, message: '리스트에서 해당 IP를 찾을 수 없습니다.' });
        }

    } catch (err) {
        console.error("IP Check error:", err);
        res.status(500).json({ error: err.message });
    }
});

app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

exports.app = app;

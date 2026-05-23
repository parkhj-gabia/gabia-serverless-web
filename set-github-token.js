const admin = require('firebase-admin');

// Initialize with the project ID
try {
    admin.initializeApp({
        projectId: 'gabia-serverless-app'
    });
} catch (e) {
    console.error("Firebase initialization failed:", e.message);
    process.exit(1);
}

const db = admin.firestore();
const token = process.argv[2];

if (!token) {
    console.log("사용법: node set-github-token.js <본인의_GITHUB_TOKEN>");
    process.exit(1);
}

console.log("Firestore에 토큰 저장 시도 중...");

db.collection('config').doc('github').set({ token })
    .then(() => {
        console.log("✅ 성공적으로 Firestore의 'config/github' 문서에 토큰을 저장했습니다!");
        process.exit(0);
    })
    .catch((err) => {
        console.error("❌ 토큰 저장 실패:", err.message);
        console.error("gcloud 로그인 상태인지 확인하거나 Application Default Credentials가 잘 잡혀있는지 확인해주세요.");
        process.exit(1);
    });

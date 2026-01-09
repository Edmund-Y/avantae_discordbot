# Discord 자동 나가기 봇

DM에서 `/자동나가기` 명령어를 사용하면 지정한 시간 후 음성 채널에서 자동으로 연결 해제됩니다.

## 설치 방법

### 1. Python 패키지 설치
```powershell
pip install -r requirements.txt
```

### 2. Discord Bot 설정
1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. `New Application` → 앱 생성
3. `Bot` 메뉴 → `Reset Token` → 토큰 복사
4. `Privileged Gateway Intents` 활성화:
   - `SERVER MEMBERS INTENT` ✅
   - `MESSAGE CONTENT INTENT` ✅

### 3. 환경 변수 설정
`.env.example`을 `.env`로 복사하고 토큰 입력:
```
DISCORD_TOKEN=your_bot_token_here
```

### 4. 봇 초대
Developer Portal → OAuth2 → URL Generator:
- **Scopes**: `bot`, `applications.commands`
- **Bot Permissions**: `Connect`, `Speak` (음성 채널 권한)

생성된 URL로 서버에 봇 초대

## 실행
```powershell
python bot.py
```

## 사용법

봇에게 **DM**으로 명령어 사용:

| 명령어 | 설명 |
|--------|------|
| `/자동나가기` | 자동 나가기 설정 (시간 입력 모달) |
| `/자동나가기취소` | 설정된 타이머 취소 |

### 기능
- ⏳ **실시간 카운트다운**: Embed에서 1초마다 남은 시간 자동 업데이트
- 📊 **프로그레스 바**: 시각적으로 남은 시간 확인
- 🔘 **버튼**: 취소 또는 시간 변경 가능


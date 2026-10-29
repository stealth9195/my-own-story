---
paths:
  - "backend/app/api/**"
  - "backend/app/main.py"
  - "backend/app/config.py"
  - "backend/tests/api/**"
  - "backend/.env.example"
---
# 서비스 API 규칙 (저장 없음)

- 서버는 이야기를 저장하지 않는다. 구간마다 HMAC 서명을 붙여 돌려주고, 프론트가 다음 요청에 지난 구간 전체를 서명과 함께 보낸다.
  - 왜: DB 없이 마감(11/3)을 맞추기로 함(2026-10-29). 책장·이어하기는 프론트 IndexedDB.
  - 서명에는 story(id·카드·선택 횟수·목소리)·index·구간이 함께 들어간다. 본문을 고치면 400 `bad_signature` → 자유 입력(프롬프트 주입) 차단.
  - `STORY_SECRET` 은 32자 이상. 바꾸면 진행 중인 이야기는 이어지지 않는다.
- 한도는 서버 메모리에서 센다(재시작하면 0). 실제 한도는 Gemini·Typecast 가 막으므로 넘쳐도 과금은 없고 그 구간이 글만 나온다.
  - 이야기 수: 익명 ID당·전체 하루(KST). 같은 구간 다음 요청은 2번까지(반복 요청으로 LLM 한도 소진 방지).
  - Gemini TTS: 모델마다 하루 10회, **태평양 시간 자정** 초기화(KST 16~17시). 이야기 시작 때 구간 수만큼 예약, 예약을 넘는 호출(재시도·두 번째 요청)은 사용량에 더한다.
  - TTS 429·402 는 다시 부르지 않는다(바로 불러도 실패하고 한도만 씀).
- LLM: 기본 → 예비(순서대로), 대비 모델(Gemma)은 기본과 동시에 출발해 둘 다 실패하면 먼저 통과한 글을 쓴다. 모두 Google 모델이라 키는 `GEMINI_API_KEY` 하나.
- 기록은 DB 대신 `log_event` 로 JSON 한 줄(Cloud Run 로그). API 키·서명 비밀값은 넣지 않는다(`test_log_has_no_secret`).
- `.env` 의 JSON 목록(`BACKUP_MODELS`, `CORS_ORIGINS`)은 작은따옴표로 감싼다.
  - 겪은 버그: `uv run --env-file` 이 큰따옴표를 지워 `["a"]` → `[a]` 가 되어 서버가 시작하지 않았다.
- 빈 주소 줄(`PRIMARY_BASE_URL=`)은 기본 주소(Gemini)로 처리한다. 예전 `.env.example` 을 복사한 `.env` 에 남아 있었다.
- Windows 콘솔에서는 로그의 한글이 깨져 보인다(cp949). Cloud Run(Linux)에서는 UTF-8.

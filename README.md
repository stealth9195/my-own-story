# 나만의 이야기 (My own story)

4~7세 아이가 좋아하는 카드와 선택지를 고르면, AI 가 그에 맞춰 이야기를 이어 만들고 읽어 주는 구연동화 웹앱(PWA)입니다.

## 화면 흐름

1. 홈 → **새 이야기 만들기**
2. 처음 선택 4단계: 주인공·장소·물건 등 카드를 고른다 (한 번 누르면 이름을 읽고, 한 번 더 누르면 고름)
3. 읽기: 그림 장면 + 글 + 이야기 음성. 페이지는 음성에 맞춰 넘어간다
4. 선택지: 다음 이야기를 아이가 고른다 → 3으로
5. 결말 → **내 책장**에 저장, 나중에 다시 듣기·이어 듣기

## 기술 스택

| 영역 | 사용 |
|---|---|
| 프론트 | React 19, Vite, TypeScript, 일반 CSS, PWA(vite-plugin-pwa), IndexedDB(책장) |
| 백엔드 | FastAPI(Python 3.12, uv). 이야기를 저장하지 않음 |
| 이야기 생성 | Gemini Flash Lite 두 모델 동시 호출 |
| 음성 | 이야기: Gemini TTS, 안내·선택지: Azure 음성(무료 F0) |
| 배포 | Cloudflare Pages(프론트), Render 무료(백엔드) — `docs/deploy.md` |

## 로컬 실행 (Windows cmd)

```bat
cd backend
copy .env.example .env
uv sync
uv run --env-file .env uvicorn --factory app.main:build_app --port 8001
```

```bat
cd frontend
npm ci
npm run dev
```

`http://localhost:5173` 을 연다. `.env` 에는 `GEMINI_API_KEY`, `STORY_SECRET`(32자 이상), `PRIMARY_MODEL`, `SECONDARY_MODEL` 이 필요하다.

테스트: `backend` 에서 `uv run pytest`, `frontend` 에서 `npm test` (외부 API 를 부르지 않음).

## 설계 판단

- **운영비 0원**: 모든 외부 서비스를 무료 요금제로. 그래서 하루 이야기 수·음성 횟수에 한도가 있다.
- **서버에 저장하지 않음**: DB 없이 구간마다 서명(HMAC)을 붙여 돌려주고, 이야기는 기기의 IndexedDB 에 둔다. 글을 고쳐 보내면 서명이 맞지 않아 거절된다(프롬프트 주입 방지).
- **이야기 생성 속도**: 두 모델을 동시에 불러 먼저 검사를 통과한 글을 쓴다. 출력은 JSON 으로 받고 검사기로 확인한다(목록 밖 그림 ID, 끊긴 문장 등).
- **그림 고르기**: 임베딩 검색 없이 프롬프트에 그림 목록을 넣고 ID 만 고르게 한다.
- **음성이 막힐 때**: 같은 목소리 이름으로 다른 Gemini TTS 모델이 대신 읽는다. 다른 목소리로 바꾸면 중간에 목소리가 확 달라져서 그렇게 하지 않는다.
- **글 못 읽는 아이**: 선택은 두 번 누르기(첫 터치는 이름 읽기), 버튼은 크게, 글보다 그림.

## 에셋 출처

- 그림: ComfyUI + FLUX.1 schnell 로 직접 생성 (`assets/image-prompts.html`)
- 배경 음악: ElevenLabs 로 직접 제작
- 효과음: Pixabay — [`frontend/public/sound/SOURCES.md`](frontend/public/sound/SOURCES.md)

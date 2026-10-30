# HANDOFF — 다음 세션 시작 안내

작성: 2026-10-30 · 브랜치 `feature/story-core` (master 에 아직 안 합침, 원격 저장소 없음)

## 다음 세션에서 "native로 작업 시작하자" 라고 하면

**4차 계획을 Native(superpowers:executing-plans)로 실행한다.**

- 계획: `docs/superpowers/plans/2026-10-29-04-assets-sound-pwa-deploy.md` (아직 커밋 안 됨 → 시작할 때 `[문서] 4차 계획` 으로 커밋)
- 기획안: `docs/superpowers/specs/2026-10-28-my-own-story-design.md`
- 순서: Task 1 그림 변환 스크립트 → 2 장면 조립·상태 효과 → 3 효과음·음악·음소거 → 4 PWA → 5 배포 준비 → 6 실제 배포(사용자와 함께)
- 마감: **2026-11-03(화) 발표.** 11/1(일) 작업 불가, 11/2(월) 저녁 불가

### 시작 전에 확인할 것

1. 커밋 방식: 2·3차 때 사용자가 "테스트 통과 시 자동 커밋"을 허락했다. 4차도 같은지 Task 1 끝에 한 번 묻는다.
2. `CLAUDE.md` 8절(배포)이 아직 "백엔드 Google Cloud Run 예정"이다. 결정은 **Render 무료**로 바뀌었으니 Task 5 문서 갱신 때 같이 고친다.
3. 효과음 파일 10개가 이미 `frontend/public/sound/` 에 있다(사용자가 받음, 커밋 안 됨). 배경 음악은 아직 없음 — 사용자가 직접 만들어 3개 이상 넣을 수 있음.
4. 그림은 사용자가 ComfyUI 로 만드는 중. 아직 `assets/raw/` 폴더도 없다. 파일 이름 = catalog id (`bear.png`), 캐릭터·사물 1024², 배경 1344×768.

## 4차 확정 사항 (사용자 결정)

| 항목 | 결정 |
|---|---|
| 그림 | `assets/raw/{id}.png` → 스크립트(rembg 배경 제거 + WebP) → `frontend/public/img/`. 없는 그림은 이모지. `assets/raw/` 는 git 제외 |
| 소리 | 넣는다. 파일은 사용자가 준비(Pixabay·직접 제작). 음악은 catalog `bgm` 에 `{id, name, mood}` 추가로 늘릴 수 있게 |
| 백엔드 배포 | **Render 무료** (카드 없음, 15분 쉬면 잠듦 → 홈에서 미리 깨우기). Cloud Run 은 카드 등록·과금 위험 때문에 안 씀 |
| 프론트 배포 | **Cloudflare Pages** |
| 음소거 | 음악·효과음만 끔. 이야기 음성은 계속 (계획 작성 시 Claude 가 정함) |

## 지금까지 한 일 (이번 세션, 21커밋)

- **기획안 정리**: 음성은 구간 단위, TTS 는 Gemini 기본 → 한도 소진 시 Typecast → 브라우저 TTS, 선택 기본 4회, 프롬프트 v8 반영
- **2차 백엔드 (저장 없는 서비스 API)** — `backend/app/main.py`, `backend/app/api/*`, 규칙 `.claude/rules/api.md`
  - DB 없음. 구간마다 HMAC 서명 → 프론트가 지난 구간을 서명째 다시 보냄(본문 조작 차단)
  - API: `GET /api/start-options`, `POST /api/stories`, `POST /api/stories/next`, `POST /api/tts`(MP3), `POST /api/events`
  - 한도는 서버 메모리(재시작 시 초기화): 익명 ID당 하루 3편, 전체 30편, 같은 구간 다음 요청 2번, TTS 구간당 2번. Gemini TTS 한도는 태평양 시간 자정 기준
  - LLM: `gemini-3.5-flash-lite` + `gemini-3.1-flash-lite` **동시 호출**, 먼저 통과한 글 사용 → 구간당 10~25초에서 2~4초로(1편 실측, 매번 3.1 이 먼저). Gemma 대비 모델은 `.env` 에 주석으로만
  - 키는 `GEMINI_API_KEY` 하나(+ `TYPECAST_API_KEY`, `STORY_SECRET` 32자 이상)
- **3차 프론트 MVP** — `frontend/`, 규칙 `.claude/rules/frontend.md`
  - React 19 + Vite 8 + TS, 일반 CSS, 라우터 없이 `App.tsx` 의 `screen` 상태
  - 홈 → 처음 선택 4단계(두 번 눌러 고르기, 질문 읽어 주기) → 읽기(글 먼저, 구간 음성 오면 자동 재생·자동 페이지 넘김) → 선택지 → 결말(다시 듣기) → 책장(IndexedDB, 이어하기)
  - 질문·선택지 읽기는 브라우저 `speechSynthesis`(서버 TTS 한도 보호). 아이폰 대비 첫 터치에서 `unlockAudio()`
  - 테스트: Vitest 25개(jsdom + Testing Library 로 Reading 화면 테스트 포함)
- 리뷰: 2·3차 모두 브랜치 전체 리뷰(Opus 서브에이전트) 후 Important 수정 완료

## 실행

```bat
:: 백엔드 (backend 폴더) — .env 에 GEMINI_API_KEY, STORY_SECRET, PRIMARY_MODEL, SECONDARY_MODEL 필요
uv run --env-file .env uvicorn --factory app.main:build_app --port 8001
uv run pytest

:: 프론트 (frontend 폴더) — /api 는 Vite 프록시로 8001 에 넘어감
npm run dev
npm test
npm run build
```

`.claude/launch.json` 에 `story-api`(8001), `story-web`(5173), `story-lab`(8000) 이 있다.

## 사용자 작업 스타일 (꼭 지킬 것)

- 한국어, 짧게. 사용자가 선택지로 고른 대로 고쳤으면 "고른 대로 고쳤어요" 한 줄만 — 수정 내역을 다시 풀어 쓰지 않는다
- 정해지지 않은 것은 선택지(장단점·예시)로 묻는다. 이해하기 어려우면 그림·예시로 설명
- 의견을 물으면 코드는 고치지 않고 의견만
- push·저장소 만들기·master 합치기·배포 연결은 사용자 요청/승인 후에만
- 사용자는 React 처음 → 처음 나오는 개념에 짧은 주석

## 알아 둘 함정

- `uv run --env-file` 은 큰따옴표를 지운다 → `.env` 의 JSON 목록은 작은따옴표로 (`CORS_ORIGINS='["..."]'`)
- React StrictMode 는 개발 중 useEffect 를 두 번 실행 → 서버 요청이 두 번 가면 구간당 2번 한도를 다 씀. `Reading.tsx` 의 `audioRequests`·`requesting` 로 막아 둠
- Windows 콘솔·preview 로그에서 한글이 깨져 보인다(cp949). 실제 데이터는 정상
- 실제 LLM·TTS 호출은 무료 한도를 쓴다(Gemini TTS 모델당 하루 10회). 브라우저 확인은 필요한 만큼만

## 남은 문제 (미룬 것)

- 백엔드: 동시 시작 시 초과 예약, 시작 실패에도 한도 차감, anon_id 바꿔 전체 한도 소진
- 프론트: 중간에 떠날 때 음성 object URL 해제 안 함, 홈 "내 책장" 버튼은 unlockAudio 안 부름, 선택 후 저장을 기다리지 않음
- 확인 필요(사용자): 구간 중간 새로고침 후 이어하기가 그 구간의 선택지부터 시작하는 동작이 괜찮은지
- 아이폰 실제 소리 재생 미확인
- 글 품질: 같은 문장 반복, 문장형 선택지와 앞 문장 흐름이 어색한 경우, 문장 사이 띄어쓰기 누락 (프롬프트 쪽)
- `run_generate` 기본 프롬프트가 v1 — `--version` 으로 지정

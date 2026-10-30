# HANDOFF — 다음 세션 시작 안내

갱신: 2026-10-30 저녁 · 작업 브랜치 `feature/assets-sound-pwa` (master 에 아직 안 합침, push 안 함) · 원격 `origin` = https://github.com/stealth9195/my-own-story (master 까지만 올라가 있음)

## 다음에 할 일

**4차 계획 Task 5 → 6 을 이어서 한다** (`superpowers:executing-plans`, 작업 기록은 `.superpowers/sdd/2026-10-29-04-assets-sound-pwa-deploy/progress.md` — git 제외)

- 계획: `docs/superpowers/plans/2026-10-29-04-assets-sound-pwa-deploy.md`
- Task 1~4 끝. 이후 사용자 확인으로 바뀐 것이 많다 → `CLAUDE.md` 진행 상황과 `.claude/rules/*.md` 가 최신 기준
- **Task 5 배포 준비**: Render 설정(`render.yaml`), `docs/deploy.md`(순서·환경 변수), 홈에서 서버 미리 깨우기, `CLAUDE.md` 8절
  - 환경 변수에 새로 생긴 것: `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`(안내 목소리), `PROMPT_VERSION=v9`
  - 첫 push 전에 비밀 값(.env, 키) 검사
- **Task 6 실제 배포**: 사용자와 함께 (저장소 연결·배포 서비스 연결은 사용자 승인 후)
- 끝나면: 브랜치 전체 리뷰(서브에이전트) → 사용자 승인 후 master 합치기
- 마감: **2026-11-03(화) 발표.** 11/1(일) 작업 불가, 11/2(월) 저녁 불가

## 시작 전에 확인할 것

1. 커밋 방식: 4차는 "테스트 통과 시 자동 커밋" 허락 받음
2. 사용자 확인 대기 중: 이야기 음성 끝 '콱' 소리가 없어졌는지 (끝 0.8초 전부터 줄이고 0.3초 전에 멈춤 + 멈춘 직후 음량 복원 안 함, `frontend/src/audio.ts`). 안 되면 음악 켬/끔, 처음 듣기/다시 듣기, 브라우저를 나눠 원인 좁히기
3. 기획안(PRD)은 본문을 고치지 않고, 배포가 끝난 뒤 실제 결과물과 비교한다(사용자 결정, `prd-match-report` 스킬)

## 오늘(2026-10-30) 한 일 요약

- 그림 63장 WebP 변환 스크립트(`backend/tools/assets.py`), 흰 물체 3장(편지·유니콘·배)은 두 모델 합치기
- 장면: 마주 보게 배치·반전, 밤·노을 색, 사물 위치(머리·손·하늘), 간격 조절(`scene.ts` 의 `ACTOR_SPREAD`)
- 소리: 배경 음악 6곡·효과음 10개(`frontend/public/sound/SOURCES.md`), 음소거, 효과음 2초 뒤
- PWA, 앱 아이콘(토끼, `backend/tools/icons.py`)
- 읽기 화면: 가로 두 칸, 읽은 글 쌓기, 버튼 아래 고정, 만드는 중 덮개, 일시정지, 이어 듣기, 다시 들을 때 이전/다음
- 설정 창: 소리 크기·배속·이야기 목소리(미리 듣기)·안내 목소리(Azure)
- TTS: 연출 지시 통일, 다른 Gemini 모델로 대신 읽기, 하루 한도 기억, 실패 이유 기록
- 프롬프트 v9 + 검사기(중간 페이지 '...' 끊김)
- 실험은 모두 별도 워크트리에서 하고 사용자 확인 후 합쳤다 (지금 남은 워크트리 없음)

## 실행

```bat
:: 백엔드 (backend 폴더) — .env 에 GEMINI_API_KEY, STORY_SECRET, PRIMARY_MODEL, SECONDARY_MODEL, AZURE_SPEECH_KEY/REGION, PROMPT_VERSION=v9
uv run --env-file .env uvicorn --factory app.main:build_app --port 8001
uv run pytest

:: 프론트 (frontend 폴더) — /api 는 Vite 프록시로 8001 에 넘어감
npm run dev
npm test
npm run build
```

`.claude/launch.json`: `story-api`(8001), `story-web`(5173), `story-lab`(8000), `story-web-build`(4173, 빌드 미리보기).
개발 확인 화면: `http://localhost:5173/?demo`, `?demo=reading` (서버 없이).

## 사용자 작업 스타일 (꼭 지킬 것)

- 한국어, 짧게. 고른 대로 고쳤으면 수정 내역을 다시 풀어 쓰지 않는다
- 정해지지 않은 것은 선택지(장단점·예시)로 묻는다. 의견을 물으면 코드는 고치지 않고 의견만
- 큰 화면 변경·실험은 워크트리(`../my-own-story-<이름>`, 다른 포트)에서 보여 주고 승인 후 합친다
- push·저장소·master 합치기·배포 연결은 사용자 요청/승인 후에만
- 사용자는 React 처음 → 처음 나오는 개념에 짧은 주석
- 이미 잘 된 것까지 다시 돌리지 않는다 (예: 그림 63장 전체 재변환으로 시간 낭비 → 문제 있는 것만)

## 알아 둘 함정

- 무료 한도: Gemini TTS 모델당 하루 10회·분당 3회(태평양 자정 초기화). 서버 한도 계산은 메모리라 다시 켜면 0부터 → 실험 중 Google 429 가 잦았다. 서버 두 개(8001·8002)를 같은 키로 돌리면 더 어긋난다
- 3.x TTS 모델은 한 문장짜리 지시를 소리 내어 읽었다 → `DIRECTOR'S NOTES / TRANSCRIPT` 형식으로 해결
- rembg 기본 모델은 `bria-rmbg`(u2net 아님). 흰 물체 안쪽을 지우므로 그런 그림만 `CAREFUL_IDS`
- Python 스크립트를 셸 heredoc 으로 고칠 때 `\n`·`\x00` 이 실제 줄바꿈·널 문자로 들어간 적이 있다 → 여러 줄 수정은 Edit 도구로
- 브라우저 탭을 열어 둔 채면 배경 음악이 계속 나온다. 확인 끝나면 탭·서버를 닫는다
- `uv run --env-file` 은 큰따옴표를 지운다 → `.env` 의 JSON 목록은 작은따옴표로
- React StrictMode 는 개발 중 useEffect 를 두 번 실행 → 서버 요청 중복은 `audioRequests`·`requesting` 으로 막음
- Windows 콘솔에서 한글이 깨져 보인다(cp949). 실제 데이터는 정상

## 남은 문제

`CLAUDE.md` 의 진행 상황 '남은 문제' 참고 ('콱' 소리 확인, `per_day` 문구 확인, "나타난 것은 바로..." 반복, API 리뷰에서 미룬 작은 문제, 아이폰 미확인, 기획안 미갱신)

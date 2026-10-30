# HANDOFF — 다음 세션 시작 안내

갱신: 2026-10-31 · 4차 끝, master 에 합치고 push 함(작업 브랜치 `feature/assets-sound-pwa` 와 같음) · 원격 `origin` = https://github.com/stealth9195/my-own-story

**배포 주소**: 앱 https://my-own-story.pages.dev (Cloudflare Pages) · API https://my-own-story-api.onrender.com (Render 무료). master 에 push 하면 둘 다 다시 배포된다(`docs/deploy.md`).

## 다음에 할 일 (사용자가 정한 순서)

1. **디자인 개편** — 지금 화면은 기능 확인용. 큰 변경이므로 워크트리(`../my-own-story-<이름>`, 다른 포트)에서 보여 주고 승인 후 합친다
2. **프롬프트 v1~v9 결과 품질 평가·비교** — 정해 둔 기준(`eval/judge.py` 의 `CRITERIA`, `judge_prompt.md`)으로 점수를 매겨 발표용 전후 비교. 다른 세션에서 병행할 수도 있음
3. 기획안(PRD)과 실제 결과물 비교 (`prd-match-report`, 본문은 고치지 않음)
4. 3.8 TTS 용 지시 형식 시험(B) — 무료 TTS 한도를 쓰므로 시연 뒤 추천
- 마감: **2026-11-03(화) 발표.** 11/1(일) 작업 불가, 11/2(월) 저녁 불가

## 시작 전에 확인할 것

1. 커밋 방식: 4차는 "테스트 통과 시 자동 커밋" 허락 받음. push 는 사용자 요청 때만
2. 시연은 아이폰이 아님 → 아이폰 음량 문제(설정 크기·음악 줄이기 안 됨)는 고치지 않기로 함
3. 시연용 ElevenLabs 목소리(경상도 사투리·서울 표준어): 유료 크레딧, 설정 창에서 고른 사람만. 시연이 끝나면 Render 의 `ELEVENLABS_API_KEY` 를 지운다
4. 시연 전: 배포 주소를 미리 열어 Render 를 깨운다. Gemini TTS 는 모델당 하루 10회라 리허설로 다 쓰지 않게

## 2026-10-30~31 한 일 요약

- 그림 63장 WebP, 장면 조립(마주 보게·밤·노을·사물 위치), 배경 음악 6곡·효과음 10개, PWA·앱 아이콘, 탭 아이콘(책)
- 읽기 화면·설정 창 개선, 음성 60초 넘게 늦으면 '다음' 버튼
- TTS: 연출 지시 통일, 다른 Gemini 모델로 대신 읽기, 하루 한도 기억, 3.8 의 WAV 응답 처리('콱' 소리 원인), 음성 길이 검사
- 프롬프트 v9 + 검사기, 더듬기 오타 고치기
- 배포: Render + Cloudflare Pages. 배포 사고(키 끝 줄바꿈 → 키가 로그에 노출, 키 재발급)와 대응은 `.claude/rules/api.md`

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

`CLAUDE.md` 의 진행 상황 '남은 문제' 참고 (3.8 지시문 읽기, `per_day` 문구 확인, "나타난 것은 바로..." 반복, API·배포 전 리뷰에서 미룬 작은 문제, 기획안 미갱신)

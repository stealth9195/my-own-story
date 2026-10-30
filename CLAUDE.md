# My own story (my-own-story)

4~7세 아이가 취향 카드와 선택지로 이야기를 이어 가는 AI 구연동화 웹앱(PWA).
백엔드 FastAPI(저장 없음), 프론트 React 19(Vite, TypeScript, 일반 CSS), 책장은 브라우저 IndexedDB.
외부 API: Gemini(이야기 생성·TTS), Typecast(예비 TTS). OpenRouter·Azure 는 실험(eval)에서만.
**운영비 0원 — 무료 티어만 쓴다.** 유료 서비스·과금 위험이 있는 선택은 그 위험을 함께 알린다.
세부 규칙은 `.claude/rules/` 에 있고 해당 파일을 다룰 때 자동으로 읽힌다.

## 문서 위치

- 기획안(PRD): `docs/superpowers/specs/2026-10-28-my-own-story-design.md`
- 1차 구현 계획: `docs/superpowers/plans/2026-10-28-01-story-core-and-experiments.md`
- 원본 메모: `구연동화앱.txt` (개인 메모, git 제외)
- 기본 브랜치: `master`

## 작업 방식

### 1. 대화·진행 방식

- 모든 답변은 한국어로. 미사여구 없이 필요한 문장만. 처음 나오는 용어는 쉬운 말로 풀어 준다.
- **작은 기능 단위로** 진행하고, 한 단계가 끝나면 **사용자 확인을 받은 뒤** 다음 단계로 간다.
- 정해지지 않은 사항은 임의로 정하지 말고 **선택지(장단점 포함)를 제시해 묻는다.**
- 사용자가 **의견을 물으면 코드는 고치지 말고 의견만** 답한다.
- 사용자가 직접 실행할 명령은 쓰는 터미널 문법으로 준다(Windows cmd 면 ` ```bat `, 환경 변수는 `set "이름=값"`, PowerShell 문법은 정말 필요할 때만).
- 겪지 않은 일(에러가 났다, 테스트를 돌렸다 등)은 지어내지 않는다. 실패는 출력과 함께 그대로 보고한다.

### 2. 실험은 별도 워크트리에서

되돌릴 수도 있는 큰 변경(디자인 개편, 구조 변경, 라이브러리 교체 등)은 master 에서 바로 하지 않는다.

1. 프로젝트 **상위 폴더**에 워크트리를 만든다.
   - 폴더: `../my-own-story-<실험이름>`, 브랜치: `experiment/<실험이름>`
   ```bat
   git worktree add ..\my-own-story-<실험이름> -b experiment/<실험이름>
   ```
2. 실험 서버는 **기존 서버와 다른 포트**로 띄운다(예: 백엔드 8000→8001, 프론트 5173→5175).
   `.claude/launch.json` 에 잠시 항목을 추가하고, 휴대폰 확인이 필요하면 `--host`.
3. 사용자에게 결과를 보여주고 **승인되면** fast-forward 로 합친다.
   ```bat
   git switch master
   git merge --ff-only experiment/<실험이름>
   ```
4. 합친 뒤 워크트리·브랜치·임시 launch.json 항목을 지운다. 승인되지 않으면 master 는 그대로 두고 지운다.
   ```bat
   git worktree remove ..\my-own-story-<실험이름>
   git branch -d experiment/<실험이름>
   ```

### 3. 커밋

- 제목 형식·나눠 커밋하기·승인 후 커밋·설계 노트는 `commit-with-design-notes` 스킬을 따른다.
- 승인 요청은 짧게: 커밋별 제목 + 필요하면 파일 묶음 한 줄, 설계 노트는 '고민' 줄만.
- 패키지를 추가하면 의존성 파일과 잠금 파일(`pyproject.toml`+`uv.lock`, `package.json`+`package-lock.json`)을 함께 커밋한다.
- 기능을 마치면 문서(진행 상황·규칙 파일)를 갱신하는 `[문서]` 커밋을 따로 둔다.
- push·PR·master 합치기는 사용자가 요청할 때만.

### 4. 검증

- 백엔드를 고쳤으면 커밋·합치기 **전에** 테스트를 돌려 결과를 보고한다. **실패하면 커밋하지 않는다.** (세부: `rules/testing.md`)
- "됐다"고 말하기 전에 실제로 확인한다(테스트 출력, 화면 확인, 로그). 증거 없이 완료라고 하지 않는다.

### 5. 비밀 값

- `.env` 를 확인할 때는 값(API 키)을 **가려서** 출력한다. `.env` 는 git 에서 제외하고 `.env.example` 을 둔다.
- 로그에는 API 키·토큰을 남기지 않는다. 키는 끝 4자리만.
- git 에서 뺄 것: `.env`, 로그, `node_modules`, 빌드 결과, 개인 메모·디자인 시안 폴더.

### 6. 문서·규칙 관리

- `CLAUDE.md` 는 짧게: 앱 한 줄 설명, 기술 스택, 작업 방식, 실행 명령, 진행 상황.
- 영역별 세부 규칙은 `.claude/rules/<영역>.md` 로 나누고, 맨 위 `paths:` 에 관련 파일을 적어 **그 파일을 다룰 때만** 읽히게 한다.
  ```markdown
  ---
  paths:
    - "backend/app/llm/**"
    - "frontend/src/pages/StoryPage.tsx"
  ---
  # LLM 호출 규칙
  ```
- 규칙에는 '무엇을'뿐 아니라 **'왜'** 와 실제로 겪은 버그를 적는다.
- 진행 상황은 **완료 / 다음 후보 / 하지 않기로 함(이유) / 남은 문제** 로 나눠 적는다.
- 개발 기록(블로그·노션)은 정해 둔 글쓰기 지침을 먼저 읽고 따른다. 실제 커밋·대화에 있던 내용만 근거로 쓴다.

### 7. 개발 환경 (Windows)

- 켜 둔 `--reload`·Vite 가 파일 변경을 놓칠 때가 있다. 결과가 예전 그대로면 서버를 껐다 켠다. `.env` 변경은 항상 재시작.
- 콘솔 출력은 cp949 오류가 날 수 있다. eval 스크립트는 `eval/console.py` 로 UTF-8 로 맞춘다.
- Python 은 `uv`(`uv sync`, `uv add 이름`, `uv run …`), Node 는 `npm ci` 로 잠금 파일 그대로 설치.

### 8. 배포

- 배포 순서·환경 변수 목록은 `docs/deploy.md` 에 따로 적는다(아직 없음). 프론트 Cloudflare Pages 또는 Vercel, 백엔드 Google Cloud Run 예정.
- 배포 환경에서만 다른 점(https, CORS 주소 등)은 설정값으로 고를 수 있게 만든다.
- 로컬 전용 편의 기능(실험 서버 등)은 배포 환경에서 자동으로 꺼지게 한다.

### 나중에 넣을 규칙 (해당 기능이 생길 때)

- Supabase 도입 시: 테스트는 별도 테스트 DB(이름이 `_test` 로 끝나지 않으면 시작 안 함), 매 테스트 전 표 비우기, 스키마 변경은 마이그레이션 도구로만.
- 익명 ID·구글 로그인 도입 시: 새 API 마다 로그인 필요·남의 데이터 접근 차단 테스트(모든 API 를 훑어 401 자동 검사).
- 사용자 데이터가 생기면: 실제 데이터는 테스트로 수정·삭제하지 않고, 테스트 데이터는 `[테스트] …` 로 표시 후 지운다.
- GitHub 에 올리면: push 시 GitHub Actions 로 테스트 자동 실행.

## 실행

```bat
cd backend
copy .env.example .env
uv sync
```
`.env` 에 키·모델을 채운 뒤:

```bat
:: 이야기 생성·음성 실험 서버 (http://localhost:8000)
uv run --env-file .env uvicorn app.lab.server:app --port 8000

:: 서비스 API (http://localhost:8001/docs)
uv run --env-file .env uvicorn --factory app.main:build_app --port 8001
```

```bat
:: 프론트 (http://localhost:5173, /api 는 8001 로 넘김) — frontend 폴더에서
npm ci
npm run dev
:: 테스트·빌드
npm test
npm run build

:: 테스트 (외부 API 호출 없음)
uv run pytest

:: 모델 평가: 생성 → 익명 내보내기 → (챗봇 수동 심사, scores/*.csv) → 요약
uv run --env-file .env python -m eval.run_generate --out eval/results/<run> --version v4
uv run python -m eval.export eval/results/<run>
uv run python -m eval.summarize eval/results/<run>

:: TTS 비교
uv run --env-file .env python -m eval.tts_check
```

사용 한도 확인 (주소는 바뀔 수 있음):
- OpenRouter: https://openrouter.ai/activity
- Google AI Studio: https://aistudio.google.com/usage

## 진행 상황

- 완료:
  - 이야기 구간 데이터 모델·출력 검증기, 프롬프트 조립, OpenAI 호환 LLM 클라이언트
  - 구간 생성기(검증 실패 재시도 + 예비 모델 전환)
  - 모델 평가 도구(생성·익명 내보내기·수동 심사·요약), TTS 비교(Azure, Gemini)
  - 실험 서버·화면(lab), 프롬프트 v1~v8, Typecast TTS
  - 저장 없는 서비스 API(2차): 처음 선택 후보·이야기 시작·다음 구간·구간 음성(MP3)·사용 기록, 서명·메모리 한도 (`rules/api.md`)
  - 프론트 MVP(3차): 처음 선택 4단계 → 읽기(음성 자동 재생·자동 페이지 넘김) → 선택지 → 결말 → 책장·이어하기, 그림은 이모지 (`rules/frontend.md`)
- 다음 후보: 4차 — 그림 에셋 넣기(ComfyUI 제작 중), 효과음·음악, PWA, 배포(Cloudflare Pages + Cloud Run), 아이폰 실제 확인
- 하지 않기로 함:
  - 임베딩으로 그림·소리 매칭 — 프롬프트에 목록을 넣고 ID 만 고르게 하는 것으로 충분
  - MVP 로그인 — 기기별 익명 ID 로 시작, 구글 로그인은 이후
  - LLM 오류 종류별로 예비 모델 전환 막기 — 아이 사용 중 끊김을 줄이는 쪽을 택함(시도 기록으로 원인 확인)
  - DB(Supabase) — 마감에 맞춰 서버는 저장 없이, 책장은 프론트 IndexedDB. 기기를 바꾸면 책장 없음
  - OpenRouter(Nemotron) — 무료 하루 50회, 품질 문제. LLM 은 모두 Google 모델
- 남은 문제:
  - 구간 생성 10~25초(목표 10초 이내) → 기본·예비 동시 호출로 바꿈, 효과 측정 중
  - 서비스 API 리뷰에서 미룬 작은 문제: 동시 시작 시 초과 예약, 시작 실패에도 한도 차감, anon_id 바꿔 전체 한도 소진 등 (배포 전 확인)
  - `run_generate` 기본 프롬프트가 v1 — `--version` 으로 지정해야 함
  - 범위 축소(DB 제외, 에셋 수 등)는 프로토타입 후 결정
  - 사람 캐릭터 8개(wizard·boy·girl·grandma·grandpa·prince·chef·firefighter)는 그림·`facing` 없음(프롬프트는 있음)

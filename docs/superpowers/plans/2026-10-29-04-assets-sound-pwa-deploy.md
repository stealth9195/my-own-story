# 4차: 그림·소리·PWA·배포 구현 계획

> **에이전트 작업자용:** 필수 하위 스킬: superpowers:subagent-driven-development(권장) 또는 superpowers:executing-plans로 Task 단위 실행. 단계는 체크박스(`- [ ]`)로 추적.

**목표:** 이모지 대신 만든 그림으로 장면을 조립하고, 효과음·배경 음악을 넣고, 폰에 설치되는 PWA 로 만들어 공개 주소에 배포한다.

**구조:** 사용자가 ComfyUI 로 만든 `assets/raw/{id}.png` 를 스크립트가 배경 제거·WebP 로 바꿔 `frontend/public/img/` 에 둔다. 화면은 그림이 있으면 그림, 없으면 이모지(아직 안 만든 그림이 있어도 배포 가능). 소리 파일은 사용자가 `frontend/public/sound/{id}.mp3` 에 넣고, 없으면 조용히 건너뛴다. 프론트는 Cloudflare Pages, 백엔드는 Render 무료(카드 불필요, 15분 쉬면 잠듦 → 홈에서 미리 깨움).

**기술 스택:** rembg·Pillow(그림 변환, 개발 PC 에서만), vite-plugin-pwa, Render(Python), Cloudflare Pages

**기획안:** `docs/superpowers/specs/2026-10-28-my-own-story-design.md` (7장 그림·소리, 12장 에셋, 10장 비용)

## 전체 제약

- 운영비 0원. Render·Cloudflare 모두 무료 요금제, 카드 등록 없음
- 그림: 캐릭터·사물 1024², 배경 1344×768 PNG, 파일 이름 = catalog id. 캐릭터·사물은 배경 제거 후 512px WebP, 배경은 1024px 폭 WebP
- 그림 없으면 이모지로 대신 (에셋이 다 안 나와도 화면이 깨지지 않음)
- 소리 (기획안 7장): 배경 음악은 분위기(`mood`)별 반복 재생, 결말에서 전용 음악(`mood: "ending"`, 없으면 `warm` → `calm`). 이야기 음성 재생 중 음악 볼륨 낮춤. 효과음은 페이지당 최대 1개. 음소거 버튼(기기에 저장)
- 음악은 사용자가 더 추가할 수 있다: `shared/catalog.json` 의 `bgm` 에 `{id, name, mood}` 를 넣고 파일을 두면 된다. 같은 분위기가 여러 개면 이야기마다 무작위
- 소리 파일 출처: Pixabay(상업 이용 가능, 출처 표기 불필요), Freesound 는 CC0 만. 출처는 `frontend/public/sound/SOURCES.md` 에 적는다. 사용자가 만든 음악은 '직접 제작'
- 아이폰: 배경 음악·효과음 요소도 첫 터치에서 잠금 해제
- API 응답은 PWA 캐시에 넣지 않는다(서명된 이야기·음성은 IndexedDB 가 맡음). 그림·소리·앱 파일만 캐시
- 비밀 값(`.env`, API 키, `STORY_SECRET`)은 git 에 올리지 않는다. 첫 push 전에 검사한다
- push·저장소 만들기·배포 서비스 연결은 사용자가 하거나, 사용자 승인 후에만
- React 처음 개념은 짧게 주석, 375px 가로 넘침 없음 (`.claude/rules/frontend.md`)
- 커밋: `[유형] 제목` 한글, 테스트 통과 후. 패키지 추가 시 잠금 파일 함께

## 검토 중점

1. 그림 파일 일부만 있음(예: 곰만 있고 여우 없음) → 있는 것은 그림, 없는 것은 이모지 (Task 2)
2. 소리 파일이 하나도 없음 → 오류 없이 조용히 진행, 이야기 음성은 정상 (Task 3)
3. 음소거 중 이야기 → 배경 음악·효과음만 꺼지고 이야기 음성은 들림(구연동화의 핵심이므로) (Task 3)
4. Render 가 잠든 상태에서 첫 이야기 시작 → 홈에서 미리 깨우기 요청, 시작 요청은 대기 시간(120초) 안에 성공 (Task 5)
5. 새 버전 배포 후 폰에 옛 앱이 캐시돼 있음 → 새로 열면 새 버전으로 바뀜(자동 업데이트) (Task 4)

## 파일 구조

| 파일 | 역할 |
|---|---|
| `backend/tools/assets.py` | PNG → WebP 변환(배경 제거). `uv run --group assets python -m tools.assets` |
| `frontend/src/components/Picture.tsx` | 그림 있으면 `<img>`, 없으면 이모지 |
| `frontend/src/components/Scene.tsx` | 배경 + 캐릭터·사물 배치 + 상태 효과 + 시간대 |
| `frontend/src/scene.ts` | 순수 함수: 배치 위치, 상태 표시, 시간대 필터 |
| `frontend/src/sound.ts` | 배경 음악·효과음·음소거, 곡 고르기 |
| `frontend/vite.config.ts` | PWA 설정 |
| `render.yaml` | Render 백엔드 설정 |
| `docs/deploy.md` | 배포 순서·환경 변수 |
| `README.md` | 소개·실행 방법·에셋 출처 |

---

### Task 1: 그림 변환 스크립트

**Files:**
- Create: `backend/tools/__init__.py`, `backend/tools/assets.py`, `backend/tests/test_assets_tool.py`, `assets/raw/.gitkeep`
- Modify: `backend/pyproject.toml`(`[dependency-groups] assets = ["rembg", "pillow"]` — 배포에는 안 들어감), `.gitignore`(`assets/raw/` — 원본은 크고 시안이라 제외, CLAUDE.md 5절. 앱에 들어가는 `frontend/public/img/*.webp` 만 올림)

**Interfaces:**
- Produces:
  - `convert(src: Path, out_dir: Path, kind: str, remove_bg: Callable[[Image], Image]) -> Path` — kind `"background"` 는 배경 제거 없이 폭 1024, 그 외는 배경 제거 후 긴 변 512, WebP(quality 80)
  - `main()` — `assets/raw/*.png` 를 catalog 로 종류를 찾아 변환, 이미 최신이면 건너뜀, catalog 에 없는 파일 이름은 경고 출력

- [ ] **Step 1: 실패하는 테스트 작성** (rembg 대신 가짜 `remove_bg` 주입)

```python
def test_character_becomes_512_webp_with_alpha(): 1024² PNG → out/bear.webp, size 512², mode RGBA, remove_bg 1번 호출
def test_background_keeps_ratio_without_removal(): 1344×768 → 1024×585, remove_bg 0번
def test_unknown_id_is_skipped(): catalog 에 없는 nope.png → 변환 안 함, 경고 목록에 nope
```

- [ ] **Step 2: 실패 확인** — `uv run --group assets pytest tests/test_assets_tool.py`
- [ ] **Step 3: 구현** — `uv add --group assets rembg pillow`
- [ ] **Step 4: 통과 확인** — `uv run --group assets pytest`, 그리고 기본 `uv run pytest`(assets 그룹 없이)도 통과해야 함(테스트는 `pytest.importorskip("PIL")`)
- [ ] **Step 5: 커밋** — `[기능] 그림 변환 스크립트 추가`

---

### Task 2: 그림 표시 + 장면 조립 + 상태 효과

**Files:**
- Create: `frontend/src/components/Picture.tsx`, `frontend/src/components/Scene.tsx`(+css), `frontend/src/scene.ts`, `frontend/src/scene.test.ts`, `frontend/src/components/Picture.test.tsx`
- Modify: `screens/StartPick.tsx`, `screens/Reading.tsx`(카드·선택지·장면을 Picture/Scene 으로)

**Interfaces:**
- Produces:
  - `Picture` props: `id: string; size: number` — `img/{id}.webp`, 로드 실패(onError) 시 `emojiOf(id)` 로 바꿈
  - `scene.actorSlots(n: number): { left: number; bottom: number; scale: number }[]` — n 명을 가로로 고르게(%), 1명이면 가운데, 최대 4
  - `scene.stateMark(state: string): string | null` — talking 💬, sleeping 💤, surprised ❗, happy 💕, thinking 💭, scared 💦, walking 👣, idle null (기획안 7장 상태 효과)
  - `scene.timeFilter(time: string): string` — day `none`, sunset `sepia(0.3) saturate(1.3)`, night `brightness(0.6) saturate(0.8)`
  - `Scene` props: `scene: Page["scene"]` — 배경 그림(없으면 지금의 색+이모지), 시간대 필터, 캐릭터·사물 배치, 상태 표시는 캐릭터 머리 위에 작게 + 통통 튀기

- [ ] **Step 1: 실패하는 테스트 작성**

```ts
test("actorSlots spreads evenly"): actorSlots(1)[0].left === 50, actorSlots(3) left 오름차순, 모두 10~90
test("stateMark known and idle"): stateMark("sleeping") === "💤", stateMark("idle") === null, 모르는 값 null
test("timeFilter night darker"): timeFilter("night") 에 "brightness" 포함, timeFilter("day") === "none"
// Picture.test.tsx (jsdom)
test("falls back to emoji on error"): render → img 에 error 이벤트 → 🐻 글자 보임
```

- [ ] **Step 2: 실패 확인** — `npx vitest run`
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 + 브라우저 확인** — 테스트용으로 그림 2~3개만 넣고(사용자 그림 또는 임시 그림) 그림·이모지 섞여 보이는지, 375px 넘침 없음, 밤 장면 어두움
- [ ] **Step 5: 커밋** — `[기능] 그림 장면 조립과 상태 효과 추가`

---

### Task 3: 효과음·배경 음악·음소거

**Files:**
- Create: `frontend/src/sound.ts`, `frontend/src/sound.test.ts`, `frontend/public/sound/SOURCES.md`
- Modify: `frontend/src/audio.ts`(unlockAudio 가 음악·효과음 요소도 잠금 해제), `screens/Reading.tsx`(구간 시작 시 음악, 페이지 바뀔 때 효과음, 음성 재생 중 볼륨 낮춤), 상단에 🔇/🔊 버튼

**Interfaces:**
- Produces:
  - `pickBgm(bgm: Bgm[], mood: string, ending: boolean, rng: () => number): string | null` — ending 이면 `"ending"` → `"warm"` → `"calm"` 순서로, 아니면 같은 mood → `"calm"`. 같은 분위기 여러 곡이면 무작위. 없으면 null
  - `playBgm(id: string | null)`, `duckBgm(on: boolean)` (재생 중 0.15, 평소 0.4), `playSfx(id: string | null)`, `stopSound()`
  - `isMuted(): boolean`, `setMuted(m: boolean)` — localStorage `muted`. 음소거는 음악·효과음만, 이야기 음성은 그대로
  - 파일 없음·재생 실패는 모두 조용히 무시
  - 효과음은 페이지가 바뀔 때 그 페이지 `sfx` 1번

- [ ] **Step 1: 실패하는 테스트 작성**

```ts
test("pickBgm same mood"): mood "mystery" → "mystery_loop"
test("pickBgm falls back to calm"): mood "tense"(곡 없음) → "calm_loop"
test("pickBgm ending prefers ending then warm then calm"): ending 곡 없으면 warm, 그것도 없으면 calm
test("pickBgm random among same mood"): calm 곡 2개, rng 0.0 → 첫째, 0.99 → 둘째
test("mute persists"): setMuted(true) 후 isMuted() true (localStorage 없는 환경에서도 throw 없음)
```

- [ ] **Step 2: 실패 확인** — `npx vitest run`
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 + 브라우저 확인** — 소리 파일이 없을 때 콘솔 오류로 멈추지 않음, 파일 1~2개 넣으면 음악 재생·음성 중 작아짐·음소거 동작
- [ ] **Step 5: 커밋** — `[기능] 배경 음악·효과음·음소거 추가`

---

### Task 4: PWA (설치·캐시·자동 업데이트)

**Files:**
- Modify: `frontend/vite.config.ts`, `frontend/index.html`(theme-color, apple-touch-icon), `frontend/package.json`
- Create: `frontend/public/icon.svg`, `frontend/public/icon-192.png`, `frontend/public/icon-512.png`, `frontend/public/apple-touch-icon.png` (📖 아이콘, Pillow 로 생성 스크립트 `backend/tools/icons.py` 또는 사용자가 만든 그림)

**Interfaces:**
- Produces: `vite-plugin-pwa` 설정 — `registerType: "autoUpdate"`, manifest(`name: "나만의 이야기"`, `short_name`, `display: "standalone"`, `background_color`, `theme_color`, 아이콘), workbox: 앱 파일 미리 캐시, `img/`·`sound/` 는 CacheFirst(최대 300개), `/api/` 는 캐시하지 않음(NetworkOnly)

- [ ] **Step 1:** `npm i -D vite-plugin-pwa`, 설정
- [ ] **Step 2: 확인** — `npm run build` 후 `dist/sw.js`·`dist/manifest.webmanifest` 생성, `npm run preview` 를 브라우저로 열어 서비스 워커 등록·manifest 읽힘(개발자 도구 Application), `/api/` 요청이 서비스 워커 캐시에 없음
- [ ] **Step 3: 커밋** — `[기능] PWA 설치·캐시 추가`

---

### Task 5: 배포 준비 (설정·문서·깨우기)

**Files:**
- Create: `render.yaml`, `docs/deploy.md`, `README.md`, `frontend/.env.production.example`
- Modify: `frontend/src/screens/Home.tsx`(화면이 뜨면 `/api/start-options` 한 번 호출해 잠든 서버 깨우기), `CLAUDE.md`(배포 항목)

**Interfaces:**
- `render.yaml`: Python 웹 서비스, `rootDir: backend`, build `pip install uv && uv sync --frozen --no-dev`, start `uv run uvicorn --factory app.main:build_app --host 0.0.0.0 --port $PORT`, `plan: free`, `PYTHON_VERSION=3.12`(값 고정), 나머지 환경 변수는 이름만(`sync: false`): `GEMINI_API_KEY`, `TYPECAST_API_KEY`, `STORY_SECRET`, `PRIMARY_MODEL`, `SECONDARY_MODEL`, `PROMPT_VERSION`, `CORS_ORIGINS`
- 프론트 빌드 환경 변수: `VITE_API_BASE=https://<render 주소>`
- `docs/deploy.md`: 순서(GitHub 저장소 → Render → Cloudflare Pages → CORS 주소 맞추기), 환경 변수 표, 무료 요금제 한계(Render 잠듦·메모리 한도 초기화), 비밀 값 다루는 법
- `README.md`: 한 줄 소개, 화면 흐름, 기술 스택, 로컬 실행, 설계 판단 요약(기획안 14장), 에셋 출처(`SOURCES.md` 링크)

- [ ] **Step 1: 비밀 값 검사** — `git ls-files` 에 `.env`·`models.json`·개인 메모가 없는지, `git grep -nE "AIza|sk-or-|tc_[0-9a-f]{20,}"`(키 형태) 결과 없음 확인. 있으면 멈추고 사용자에게 알림
- [ ] **Step 2:** 파일 작성, 홈 깨우기 추가
- [ ] **Step 3: 확인** — `npm test`, `npm run build`, `uv run pytest` 통과. 로컬에서 `VITE_API_BASE=http://localhost:8001 npm run build` → `npm run preview` 로 CORS 를 거쳐 1편 생성 확인(`CORS_ORIGINS` 에 preview 주소 추가)
- [ ] **Step 4: 커밋** — `[설정] 배포 설정과 문서 추가`

---

### Task 6: 실제 배포 (사용자와 함께)

- [ ] **Step 1:** 사용자가 GitHub 저장소를 만들고, 사용자 승인 후 push (기본 브랜치에 합칠지도 이때 확인)
- [ ] **Step 2:** 사용자가 Render 에서 저장소 연결(Blueprint `render.yaml`), 환경 변수 입력
- [ ] **Step 3:** 사용자가 Cloudflare Pages 에서 저장소 연결: root `frontend`, build `npm ci && npm run build`, output `dist`, `VITE_API_BASE` 입력
- [ ] **Step 4:** Render `CORS_ORIGINS` 에 Pages 주소 넣고 재배포
- [ ] **Step 5: 확인** — 배포 주소로 1편 끝까지(PC), 폰에서 홈 화면에 추가·소리·이어하기. 아이폰 실제 확인은 사용자
- [ ] **Step 6:** `CLAUDE.md` 진행 상황·`docs/deploy.md` 갱신, `[문서]` 커밋

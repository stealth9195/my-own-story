# 3차: 프론트 MVP (처음 선택 → 읽기·음성 → 선택 → 결말 → 책장) 구현 계획

> **에이전트 작업자용:** 필수 하위 스킬: superpowers:subagent-driven-development(권장) 또는 superpowers:executing-plans로 Task 단위 실행. 단계는 체크박스(`- [ ]`)로 추적.

**목표:** 아이가 카드 4장을 고르고, 음성으로 이야기를 듣고, 선택지를 골라 결말까지 가고, 책장에서 다시 듣는 웹 화면을 만든다.

**구조:** `frontend/` 에 Vite + React + TypeScript. 화면 전환은 라우터 없이 `App` 의 상태 하나(`screen`)로 한다. 서버는 저장하지 않으므로 이야기(서명된 구간)와 음성(MP3)은 IndexedDB(`idb-keyval`)에 저장한다. 개발 중에는 Vite 프록시로 `/api` 를 백엔드(8001)에 넘겨 CORS 설정 없이 쓴다. 그림 에셋이 나오기 전까지 카드·장면은 이모지로 표시한다.

**기술 스택:** React 18, TypeScript, Vite, 일반 CSS, idb-keyval, Vitest, fake-indexeddb

**기획안:** `docs/superpowers/specs/2026-10-28-my-own-story-design.md` (5장 화면 흐름, 7장 음성)
**백엔드 API:** `backend/app/main.py`, `backend/app/api/schemas.py`, 규칙 `.claude/rules/api.md`

**범위 밖 (4차):** 장면 그림·상태 효과 애니메이션, 효과음·배경 음악, PWA, 배포

## 전체 제약

- 사용자는 React 를 처음 배운다. 처음 나오는 개념(컴포넌트, `useState`, `useEffect`, `useRef`, props)에 한두 줄 주석으로 설명한다 (`.claude/rules/frontend.md`)
- 모바일 폭 375px 에서 가로 넘침 없음. 버튼은 크게(터치 영역 최소 56px), 글보다 그림(이모지) 위주
- 사용자가 화면을 터치하기 전에는 소리를 재생하지 않는다. 아이폰 대응: 첫 터치("새 이야기 만들기")에서 공용 `HTMLAudioElement` 를 잠금 해제하고 이후 모든 이야기 음성은 그 요소 하나로 재생
- 이야기 음성은 서버 TTS(`/api/tts`, 구간 단위 MP3). `story.voice.provider === "browser"` 면 처음부터 끝까지 브라우저 `speechSynthesis`(ko-KR). 한 이야기 안에서 섞지 않는다
- 질문·선택지 읽어 주기는 무료인 브라우저 `speechSynthesis` 로 한다 (서버 TTS 한도 보호)
- 글은 바로 보여 주고, 음성이 오면 그 구간 첫 페이지부터 자동 재생. 음성이 오기 전·재생 중에는 다음 장 버튼 잠금, 페이지는 글자 수 비율로 자동 넘김. 음성 실패 시 글만 보여 주고 버튼으로 넘김
- 재생 속도는 `playbackRate`(천천히 0.85 / 보통 1.0), `localStorage` 에 저장
- 대기 화면: 로딩 바 없음. 마지막 장면 이모지가 통통 튀는 CSS 애니메이션. 15초가 넘으면 "조금만 기다려 줘" 한 번 읽기
- 처음 선택 질문 (기획안 5장 그대로): ① "이번 이야기의 주인공은 누구일까요?" ② "(주인공)은 한마디로 말하면..." ③ "어디에서, 어떤 날 일어난 이야기일까요?" ④ "(주인공)이 가지고 있던 것은?" — "이전", "다시 뽑기" 버튼
- 책장: 이야기 전부 보관, 음성은 최근 20편만(그 이전은 글만)
- 그림·소리 ID 는 `shared/catalog.json` 하나를 백엔드와 같이 쓴다
- 테스트에서 실제 API 를 부르지 않는다(`fetch` 가짜). 화면 흐름은 브라우저로 확인
- 커밋: `[유형] 제목` 한글. 사용자가 이번 계획에서 테스트 통과 시 자동 커밋을 허락하면 그대로, 아니면 승인 후. `package.json`+`package-lock.json` 함께
- 프론트 명령은 `frontend/`, 백엔드 명령은 `backend/` 에서 실행. Node 22, `npm ci`

## 검토 중점

1. 음성을 받기 전에 아이가 화면을 떠남(책장으로 이동, 새 이야기) → 이전 이야기 음성이 뒤늦게 재생되면 안 됨 (Task 5)
2. 서버가 429(`user_limit`/`total_limit`)·502(`generation_failed`)·429(`regen_limit`) → 아이에게 맞는 문장 + "다시 해볼까요?"(502만), 앱이 멈추지 않음 (Task 1, Task 5)
3. 이야기 중간에 새로고침 → 책장에 "이어하기"로 남아 같은 지점부터 계속 (Task 2, Task 6)
4. IndexedDB 를 쓸 수 없는 환경(사파리 비공개 모드 등) → 저장만 안 되고 이야기는 진행 (Task 2)
5. 아이폰에서 첫 음성이 막힘 → 첫 터치 잠금 해제 후 같은 오디오 요소 재사용 (Task 5, 아이폰 실제 확인은 사용자)

## 파일 구조

| 파일 | 역할 |
|---|---|
| `frontend/vite.config.ts` | React 플러그인, `/api` 프록시(→ `http://localhost:8001`), `@shared` 별칭, `server.fs.allow: [".."]` |
| `frontend/src/api.ts` | 타입(백엔드 스키마 그대로) + API 호출 + `ApiError` |
| `frontend/src/catalog.ts` | `shared/catalog.json` 읽기, `emojiOf(id)`, `nameOf(id)` |
| `frontend/src/storage.ts` | IndexedDB 저장 (이야기·음성), 익명 ID |
| `frontend/src/story.ts` | 순수 함수: 다음 요청 만들기, 페이지 시작 시간 계산, 제목 |
| `frontend/src/audio.ts` | 공용 오디오 요소, 잠금 해제, 브라우저 TTS 읽기 |
| `frontend/src/App.tsx` | 화면 전환 상태 |
| `frontend/src/screens/*.tsx` | `Home`, `StartPick`, `Reading`, `Shelf` (+ 같은 이름 `.css`) |
| `frontend/src/**/*.test.ts` | Vitest |

---

### Task 1: 프로젝트 + 카탈로그 이모지 + API 클라이언트

**Files:**
- Create: `frontend/` (Vite react-ts 템플릿에서 필요 없는 예시 파일 삭제), `frontend/src/api.ts`, `frontend/src/catalog.ts`, `frontend/src/api.test.ts`, `frontend/src/catalog.test.ts`
- Modify: `shared/catalog.json` (characters·objects·backgrounds 에 `emoji` 추가), `.gitignore`(`frontend/node_modules`, `frontend/dist`), `.claude/launch.json`(`story-web`: `npm run dev --prefix frontend`, port 5173)
- Test: `backend/tests/test_catalog.py` 에 테스트 추가

**Interfaces:**
- Produces (`api.ts`, 이름은 백엔드 스키마와 같게):
  - 타입 `Voice`, `StoryKey`, `Page`, `Choice`, `Segment`, `SignedSegment`, `SegmentResponse`, `StartOption`(`{id, name, kind, emoji}`), `StartOptions`(`{heroes, traits, backgrounds, objects}`)
  - `class ApiError extends Error { status: number; code: string }` — 본문 `{"detail": {"code": ...}}` 에서 code, 없으면 `"network"`(fetch 실패) 또는 `"unknown"`
  - `getStartOptions(): Promise<StartOptions>`
  - `startStory(anonId: string, cards: string[], choiceCount?: number): Promise<SegmentResponse>`
  - `nextSegment(anonId: string, story: StoryKey, history: SignedSegment[], chosen: string[]): Promise<SegmentResponse>`
  - `fetchSegmentAudio(story: StoryKey, index: number, segment: SignedSegment): Promise<Blob>`
  - `sendEvent(anonId: string, type: EventType, storyId?: string, payload?: object): void` — 실패해도 무시(기록 때문에 앱이 멈추면 안 됨)
  - API 주소: `import.meta.env.VITE_API_BASE ?? ""` + `/api/...`
- Produces (`catalog.ts`): `emojiOf(id: string): string` (없으면 `"❓"`), `nameOf(id: string): string`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_catalog.py
def test_scene_assets_have_emoji(): characters·objects·backgrounds 모든 항목에 emoji 가 비어 있지 않음
```
```ts
// api.test.ts — globalThis.fetch 를 가짜로 바꿔 요청을 기록
test("startStory posts anon_id, cards, choice_count"): URL "/api/stories", body {anon_id, cards, choice_count: 4}
test("nextSegment posts story, history, chosen")
test("error body code becomes ApiError"): 429 {"detail":{"code":"user_limit"}} → ApiError status 429, code "user_limit"
test("network failure becomes ApiError network"): fetch reject → code "network"
test("fetchSegmentAudio returns blob"): 200 audio/mpeg → Blob
test("sendEvent swallows errors"): fetch reject 해도 throw 없음
// catalog.test.ts
test("emojiOf known and unknown"): emojiOf("rabbit") 이 "❓" 가 아님, emojiOf("nope") === "❓"
```

- [ ] **Step 2: 실행해 실패 확인** — `npm test` (frontend), `uv run pytest tests/test_catalog.py` (backend)

- [ ] **Step 3: 구현** — `npm create vite@latest frontend -- --template react-ts` 후 `npm i idb-keyval`, `npm i -D vitest fake-indexeddb`. `package.json` 에 `"test": "vitest run"`. 이모지는 이름에 맞는 것으로(예: rabbit 🐰, dragon 🐉, forest 🌲)

- [ ] **Step 4: 통과 확인** — `npm test`, `uv run pytest` 전체 PASS, `npm run build` 성공

- [ ] **Step 5: 커밋** — `[기능] 프론트 프로젝트와 API 클라이언트, 카탈로그 이모지 추가`

---

### Task 2: 저장(IndexedDB) + 익명 ID

**Files:**
- Create: `frontend/src/storage.ts`, `frontend/src/storage.test.ts`

**Interfaces:**
- Consumes: `StoryKey`, `SignedSegment` (Task 1)
- Produces:
  - `type SavedStory = { story: StoryKey; segments: SignedSegment[]; chosen: string[]; createdAt: number; done: boolean }`
  - `saveStory(s: SavedStory): Promise<void>`, `getStory(id: string): Promise<SavedStory | undefined>`, `listStories(): Promise<SavedStory[]>` (최신 먼저)
  - `saveAudio(storyId: string, index: number, mp3: Blob): Promise<void>`, `getAudio(storyId: string, index: number): Promise<Blob | undefined>`
  - `pruneAudio(keep = 20): Promise<void>` — 최근 `keep` 편 밖의 음성 삭제(이야기는 남김)
  - `getAnonId(): string` — `localStorage` 에 `crypto.randomUUID()` 저장, 없으면 만듦
  - 키: `story:<id>`, `audio:<id>:<index>`
  - IndexedDB·localStorage 오류는 모두 잡아서 무시(저장 실패해도 이야기는 진행). `getAnonId` 는 localStorage 실패 시 메모리 값

- [ ] **Step 1: 실패하는 테스트 작성** — 파일 맨 위 `import "fake-indexeddb/auto"`

```ts
test("save and get story")
test("list newest first"): createdAt 1, 3, 2 → [3, 2, 1]
test("audio roundtrip")
test("prune keeps latest 20 audios"): 22편 저장 + 각 음성 → prune 후 가장 오래된 2편 getAudio undefined, 이야기는 22편 그대로
test("anon id is stable"): 두 번 호출 같은 값
test("storage errors do not throw"): idb-keyval set 이 reject 하도록 vi.mock → saveStory 가 throw 하지 않음
```

- [ ] **Step 2: 실패 확인** — `npm test`
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** — `npm test`
- [ ] **Step 5: 커밋** — `[기능] 책장 저장(IndexedDB)과 익명 ID 추가`

---

### Task 3: 이야기 계산 함수 (다음 요청, 페이지 시간, 제목)

**Files:**
- Create: `frontend/src/story.ts`, `frontend/src/story.test.ts`

**Interfaces:**
- Consumes: `SavedStory` (Task 2), `SegmentResponse` (Task 1), `nameOf`·`emojiOf` (Task 1)
- Produces:
  - `addSegment(saved: SavedStory | null, res: SegmentResponse, now: number): SavedStory` — 첫 응답이면 새로 만들고, 아니면 segments 에 덧붙임. `done = res.done`
  - `choose(saved: SavedStory, choiceId: string): SavedStory` — chosen 에 덧붙임
  - `nextArgs(saved: SavedStory): { story, history, chosen }` — `nextSegment` 에 그대로 넘길 값
  - `pageStartTimes(pages: string[], duration: number): number[]` — 각 페이지 시작 시각(초), 글자 수 비율. 첫 값 0
  - `pageAt(time: number, starts: number[]): number`
  - `storyTitle(saved: SavedStory): string` — `${emojiOf(hero)} ${nameOf(hero)} 이야기` (hero = cards[0], 예: "🦆 오리 이야기")
  - `segmentText(seg: Segment): string` — 페이지 본문을 줄바꿈으로 이음 (브라우저 TTS 용)

- [ ] **Step 1: 실패하는 테스트 작성**

```ts
test("addSegment creates then appends")
test("choose then nextArgs has same length history and chosen")
test("pageStartTimes splits by char ratio"): (["가나", "가나다라"], 6) → [0, 2]
test("pageAt picks last start not after time"): starts [0, 2, 5], time 4.9 → 1, time 5 → 2
test("storyTitle uses hero emoji and name")
```

- [ ] **Step 2: 실패 확인** — `npm test`
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** — `npm test`
- [ ] **Step 5: 커밋** — `[기능] 이야기 진행 계산 함수 추가`

---

### Task 4: 홈 + 처음 선택 4단계 + 대기 화면

**Files:**
- Create: `frontend/src/App.tsx`(교체), `frontend/src/App.css`, `frontend/src/screens/Home.tsx`, `frontend/src/screens/StartPick.tsx`, `frontend/src/screens/Waiting.tsx` (+ css), `frontend/src/audio.ts`(잠금 해제·브라우저 TTS만 먼저)
- Test: 브라우저 확인 (preview `story-web` + `story-api`)

**Interfaces:**
- Consumes: Task 1~3
- Produces:
  - `App` 상태: `screen: "home" | "pick" | "reading" | "shelf"`, `current: SavedStory | null`
  - `audio.unlockAudio(): void` (첫 터치에서 호출, 무음 재생 시도), `audio.player: HTMLAudioElement`, `audio.speak(text: string): Promise<void>` (ko-KR, 끝나면 resolve, 지원 안 되면 바로 resolve), `audio.stopAll(): void`
  - `StartPick` props: `onDone(cards: string[]): void`, `onBack(): void`. 단계마다 질문을 `speak` 로 읽고, 카드 터치 시 이름을 읽음. "이전", "다시 뽑기"(그 단계 후보만 새로 받음)
  - `Waiting` props: `emoji: string` — 15초 넘으면 `speak("조금만 기다려 줘")` 한 번

- [ ] **Step 1:** 화면 구현. 홈: "새 이야기 만들기"(누르면 `unlockAudio`), "내 책장"
- [ ] **Step 2: 브라우저 확인** — 375px 폭에서 가로 넘침 없음(`document.documentElement.scrollWidth <= 375`), 4단계 질문 문구가 기획안과 같음, 주인공 이름이 ②④ 질문에 들어감, "이전"·"다시 뽑기" 동작, 마지막 카드 터치 → 대기 화면 → `POST /api/stories` 200
- [ ] **Step 3:** `npm test`, `npm run build` 통과
- [ ] **Step 4: 커밋** — `[기능] 홈과 처음 선택 화면 추가`

---

### Task 5: 읽기 (음성 자동 재생, 페이지 넘김) + 선택지 + 결말

**Files:**
- Create: `frontend/src/screens/Reading.tsx`, `frontend/src/screens/Reading.css`
- Modify: `frontend/src/audio.ts`, `frontend/src/App.tsx`
- Test: `frontend/src/audio.test.ts` (재생 토큰), 브라우저 확인

**Interfaces:**
- Consumes: Task 1~4
- Produces:
  - `audio.playToken(): number` / `audio.isCurrent(token: number): boolean` — 화면을 떠나거나 새 이야기를 시작하면 토큰이 바뀌어, 늦게 도착한 음성은 재생하지 않음
  - `Reading` props: `saved: SavedStory`, `onUpdate(s: SavedStory): void`, `onHome(): void`
  - 흐름: 마지막 구간 글 표시 → 저장된 음성 있으면 사용, 없으면 `fetchSegmentAudio` → `saveAudio` → `player.src = URL.createObjectURL`, `playbackRate` 적용, 재생. `timeupdate` 로 `pageAt` 페이지 표시. 재생 끝 → 선택지 표시 + 선택지 이름을 `speak`. 선택 → `choose` → `saveStory` → 대기 화면 → `nextSegment` → `addSegment` → `saveStory`
  - voice browser: 페이지마다 `speak(page.text)` 후 다음 페이지
  - 선택지 3개: 물건형(`kind: "item"`)은 이모지 카드, 문장형(`"phrase"`)은 글자 버튼(그림 없음). 둘 다 터치하면 먼저 이름을 읽고, 한 번 더 터치(또는 "이걸로 할래" 버튼)하면 선택
  - 음성 실패(ApiError) → 글만, "다음 ▶" 버튼으로 넘김
  - 결말: "다시 듣기"(구간 0부터 저장된 음성으로), "새 이야기", 완료 시 `sendEvent("complete")`
  - 생성 오류 문구: `user_limit` "오늘은 이야기를 많이 들었어요. 내일 또 만나요", `total_limit` "오늘은 이야기 친구가 쉬어요", `regen_limit` 같은 문구 + 홈 버튼, `generation_failed`·`network` "다시 해볼까요?" 버튼(같은 요청 재시도)
  - 속도 버튼: 천천히/보통 (`localStorage` `speed`)

- [ ] **Step 1: 실패하는 테스트 작성**

```ts
// audio.test.ts
test("old token is not current after new token")
```

- [ ] **Step 2: 실패 확인** — `npm test`
- [ ] **Step 3: 구현**
- [ ] **Step 4: 브라우저 확인 (실제 백엔드)** — 1편을 끝까지: 음성 자동 재생, 페이지 자동 넘김, 재생 중 다음 버튼 잠금, 선택지 읽기, 결말 "다시 듣기". 음성 받는 중 홈으로 나가면 소리가 나지 않음. 백엔드를 끄고 선택 → "다시 해볼까요?" 표시. 375px 넘침 없음
- [ ] **Step 5:** `npm test`, `npm run build` 통과
- [ ] **Step 6: 커밋** — `[기능] 읽기·음성 자동 재생·선택지·결말 화면 추가`

---

### Task 6: 책장 + 이어하기 + 문서

**Files:**
- Create: `frontend/src/screens/Shelf.tsx`, `frontend/src/screens/Shelf.css`
- Modify: `frontend/src/App.tsx`, `CLAUDE.md`(스택·실행 명령·진행 상황), `.claude/rules/frontend.md`(구조·오디오 규칙과 '왜')

**Interfaces:**
- Consumes: Task 2·3·5
- Produces: `Shelf` props: `onOpen(s: SavedStory): void`, `onBack(): void`. 목록은 `storyTitle` + 날짜 + "다 들었어요"/"이어하기". 열면 완료 이야기는 결말 화면(다시 듣기), 미완료는 마지막 구간 선택지부터. 열 때 `sendEvent("replay")`. 시작할 때 `pruneAudio()`

- [ ] **Step 1:** 구현
- [ ] **Step 2: 브라우저 확인** — 이야기 중간에 새로고침 → 책장에 "이어하기" → 같은 선택지부터 계속. 완료 이야기 "다시 듣기"가 네트워크 요청 없이 재생(저장된 음성)
- [ ] **Step 3:** `npm test`, `npm run build`, 백엔드 `uv run pytest` 통과
- [ ] **Step 4:** 문서 갱신, `[문서]` 커밋

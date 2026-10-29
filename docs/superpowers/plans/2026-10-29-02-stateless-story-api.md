# 2차: 저장 없는 이야기 API 구현 계획

> **에이전트 작업자용:** 필수 하위 스킬: superpowers:subagent-driven-development(권장) 또는 superpowers:executing-plans로 Task 단위 실행. 단계는 체크박스(`- [ ]`)로 추적.

**목표:** 프론트가 붙을 서비스 API(처음 선택 후보, 구간 생성, 구간 음성, 사용 기록)를 DB 없이 만든다.

**구조:** 서버는 이야기를 저장하지 않는다. 구간마다 서명(HMAC)을 붙여 돌려주고, 프론트가 다음 요청에 지난 구간 전체를 서명과 함께 보내면 서버가 서명을 확인한 뒤 이어서 생성한다. 이야기·음성 보관은 프론트 IndexedDB(3차)가 맡는다. 한도는 서버 메모리에서 세고, 기록은 표준 출력에 JSON 한 줄씩 남긴다(Cloud Run 로그).

**기술 스택:** Python 3.12, FastAPI, pydantic 2, pydantic-settings, httpx, lameenc(WAV→MP3), pytest

**기획안:** `docs/superpowers/specs/2026-10-28-my-own-story-design.md`

**기획안과 다른 점 (2026-10-29 결정):** DB(Supabase) 없이 진행. 8장 표·6장 API 경로 대신 이 문서의 API를 쓴다. 책장·이어하기는 프론트 IndexedDB. 사용 기록은 서버 로그.

## 시작 전 확인

- 작업 폴더에 커밋하지 않은 Typecast·실험 서버 변경(`app/tts/typecast.py`, `app/lab/*`, `.env.example`, 관련 테스트)이 있다. 이 계획은 `app/tts/typecast.py` 를 쓰므로 **먼저 사용자 승인을 받아 그 변경을 커밋**한 뒤 시작한다.
- `uv run pytest` 가 전부 통과하는 상태에서 시작한다.

## 전체 제약

- 운영비 0원. 테스트에서 LLM·TTS 를 실제로 부르지 않는다(`tests/conftest.py` 의 `FakeLLM`, 가짜 TTS 함수)
- 테스트에서 `Settings()` 를 인자 없이 만들지 않는다(`.env` 가 새어 들어옴). 값을 직접 넣는다
- 선택 횟수: 설정값, 기본 4, 범위 2~5. 구간 = 발단 1 + 중간 (선택 횟수 - 1) + 결말 1. 코드 안 구간 이름은 기존대로 `intro`/`middle`/`ending`
- 프롬프트 기본 버전 `v8`. 생성은 관대한 모드(`lenient=True`)
- 자유 입력 없음: 프론트가 보낸 이야기 내용은 서버 서명이 맞을 때만 받는다
- 음성: 구간 단위 1회 생성. Gemini TTS 기본 → 하루 한도 소진 시 Typecast → 그것도 부족하면 브라우저 TTS. 한 이야기 안에서 목소리 고정
- Gemini TTS 한도: 모델마다 하루 10회. Typecast: 월 15,000자
- Gemini TTS 에 연출 지시문을 붙이지 않는다(`style="normal"`). 속도는 프론트 `playbackRate`
- 한도: 익명 ID당 하루 3편(`DAILY_STORIES_PER_USER`), 전체 하루 상한(`DAILY_STORIES_TOTAL`). 날짜는 한국 시간(KST) 기준
- 로그에 API 키·서명 비밀값을 남기지 않는다
- 커밋: `[유형] 제목` 한글, 사용자 승인 후. 본문 끝 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. 패키지 추가 시 `pyproject.toml`+`uv.lock` 함께
- 모든 명령은 `backend/` 에서 실행

## 검토 중점

1. 프론트가 지난 구간 본문을 고쳐 보냄(문장 끼워 넣기) → 400 `bad_signature`, LLM 호출 없음 (Task 1, Task 4)
2. 이야기 도중 서버가 재시작됨(Cloud Run 이 꺼졌다 켜짐) → 같은 `STORY_SECRET` 이면 다음 구간이 그대로 이어짐 (Task 4)
3. 같은 익명 ID로 4번째 이야기 시작 → 429 `user_limit`. 이미 시작한 이야기의 다음 구간은 막지 않음 (Task 4)
4. TTS 가 두 번 연속 실패(Gemini 429 포함) → 502 `tts_failed`, 프론트는 글만 표시 (Task 5)
5. 한국 시간 자정이 지나면 하루 한도가 초기화됨 (Task 2)

## 파일 구조

| 파일 | 역할 |
|---|---|
| `app/config.py` (수정) | 서비스 설정 추가, 프롬프트 기본값 v8 |
| `app/story/start.py` (신규) | 처음 선택 후보 뽑기, 구간 순서 — 실험 서버와 공용 |
| `app/api/schemas.py` | 요청·응답 모델 (`Voice`, `StoryKey`, `SignedSegment` 등) |
| `app/api/signing.py` | 구간 서명·확인 |
| `app/api/limits.py` | 메모리 한도 (이야기 수, TTS 예약, 구간별 TTS 횟수) |
| `app/api/voice.py` | 이야기 시작 시 목소리 결정 |
| `app/api/audio.py` | WAV → MP3 |
| `app/api/tts_service.py` | 구간 음성 생성 (재시도 1회, MP3 변환) |
| `app/api/log.py` | JSON 한 줄 로그 |
| `app/main.py` | `create_app(...)`, 실행용 `build_app()` |
| `tests/api/test_*.py` | Task 별 테스트 |

---

### Task 1: 설정 + 요청 모델 + 구간 서명

**Files:**
- Modify: `app/config.py`
- Create: `app/api/__init__.py`, `app/api/schemas.py`, `app/api/signing.py`
- Test: `tests/api/test_signing.py`

**Interfaces:**
- Produces:
  - `Settings` 추가 필드: `story_secret: str`, `gemini_api_key: str = ""`, `typecast_api_key: str = ""`, `daily_stories_per_user: int = 3`, `daily_stories_total: int = 30`, `cors_origins: list[str] = ["http://localhost:5173"]`. `prompt_version` 기본값 `"v8"`
  - `schemas.Voice(provider: Literal["gemini","typecast","browser"], model: str | None = None, voice: str | None = None)`
  - `schemas.StoryKey(id: str, cards: list[str] (3~5개), choice_count: int (2~5), voice: Voice)`
  - `schemas.SignedSegment(segment: Segment, sig: str)`
  - `signing.sign_segment(secret: str, story: StoryKey, index: int, segment: Segment) -> str`
  - `signing.verify_history(secret: str, story: StoryKey, history: list[SignedSegment]) -> list[Segment]` — 하나라도 틀리면 `BadSignature`
  - `signing.BadSignature(Exception)`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/api/test_signing.py`

```python
def test_roundtrip(): verify_history(S, KEY, [SignedSegment(segment=seg, sig=sign_segment(S, KEY, 0, seg))]) == [seg]
def test_edited_text_rejected(): 첫 페이지 text 를 바꾸면 BadSignature
def test_wrong_index_rejected(): index 1 로 서명한 구간을 0번 자리에 넣으면 BadSignature
def test_other_story_rejected(): KEY.id 또는 voice 가 다르면 BadSignature
def test_other_secret_rejected(): 다른 비밀값으로 서명하면 BadSignature
def test_settings_defaults(): Settings(primary_base_url="x", primary_api_key="k", primary_model="m", story_secret="s").prompt_version == "v8"
```

- [ ] **Step 2: 실행해 실패 확인** — `uv run pytest tests/api/test_signing.py -v` → ImportError

- [ ] **Step 3: 구현**
  - 서명 대상: `json.dumps({"story": story.model_dump(mode="json"), "index": index, "segment": segment.model_dump(mode="json")}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))` 의 HMAC-SHA256 16진 문자열
  - 비교는 `hmac.compare_digest`

- [ ] **Step 4: 통과 확인** — `uv run pytest -v` 전체 PASS

- [ ] **Step 5: 커밋 (승인 후)** — `[기능] 서비스 설정과 구간 서명 추가`

---

### Task 2: 한도 + 목소리 결정

**Files:**
- Create: `app/api/limits.py`, `app/api/voice.py`
- Test: `tests/api/test_limits.py`, `tests/api/test_voice.py`

**Interfaces:**
- Consumes: `schemas.Voice`, `app.tts.gemini.MODELS/VOICES`, `app.tts.typecast.MODELS/VOICES`
- Produces:
  - `limits.Limits(per_user: int, total: int, clock: Callable[[], datetime] = 현재 시각)`
    - `try_start_story(anon_id: str) -> Literal["ok","user_limit","total_limit"]` — ok 일 때만 개수 증가
    - `gemini_left(model: str) -> int` (하루 10 − 예약), `reserve_gemini(model: str, calls: int) -> None`
    - `typecast_left() -> int` (월 15,000 − 예약), `reserve_typecast(chars: int) -> None`
    - `allow_tts(story_id: str, index: int) -> bool` — 같은 구간은 하루 2번까지(첫 시도 + 다시 시도)
  - `voice.pick_voice(limits: Limits, choice_count: int, rng: random.Random) -> Voice`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# test_limits.py (clock 은 KST 기준 datetime 을 돌려주는 가짜 함수)
def test_user_limit(): 같은 anon_id 3번 "ok", 4번째 "user_limit"
def test_total_limit(): total=2 → 서로 다른 ID 3번째에서 "total_limit"
def test_resets_at_kst_midnight(): KST 23:59 에 3번 쓴 뒤 clock 을 다음날 00:00 으로 → "ok"
def test_gemini_reserve(): reserve_gemini(m, 5) 후 gemini_left(m) == 5
def test_typecast_monthly(): reserve_typecast(15000) 후 typecast_left() == 0, 다음 달 1일엔 15000
def test_allow_tts_twice(): allow_tts("a", 0) True, True, 세 번째 False

# test_voice.py
def test_first_gemini_with_room(): 한도 여유 → Voice(provider="gemini", model=MODELS[0]), voice 는 gemini VOICES 중 하나, gemini_left 가 choice_count+1 만큼 줄어듦
def test_skips_full_model(): MODELS[0] 에 6회 예약 + choice_count 4(필요 5) → MODELS[1]
def test_typecast_when_gemini_full(): 모든 Gemini 모델 남은 횟수 4 → provider "typecast", typecast_left 1,000 감소
def test_browser_when_all_full(): Gemini 가득 + typecast_left 999 → Voice(provider="browser")
```

- [ ] **Step 2: 실행해 실패 확인** — `uv run pytest tests/api -v`

- [ ] **Step 3: 구현** — 카운터는 `dict[(날짜 또는 월, 키)] → int`. 날짜는 `clock().astimezone(ZoneInfo("Asia/Seoul"))`. Typecast 예약량은 1편 1,000자로 고정(`TYPECAST_CHARS_PER_STORY = 1000`). Windows 에서 `ZoneInfo` 가 실패하면 `timezone(timedelta(hours=9))` 사용

- [ ] **Step 4: 통과 확인** — `uv run pytest -v`

- [ ] **Step 5: 커밋 (승인 후)** — `[기능] 메모리 한도와 목소리 결정 추가`

---

### Task 3: 음성 MP3 변환 + 구간 음성 생성

**Files:**
- Create: `app/api/audio.py`, `app/api/tts_service.py`
- Modify: `pyproject.toml`, `uv.lock` (`uv add lameenc`)
- Test: `tests/api/test_audio.py`, `tests/api/test_tts_service.py`

**Interfaces:**
- Consumes: `schemas.Voice`, `app.tts.gemini.synthesize/TTSError`, `app.tts.typecast.synthesize`
- Produces:
  - `audio.wav_to_mp3(wav: bytes, kbps: int = 48) -> bytes` — 모노 16비트 WAV(24kHz·44.1kHz)
  - `tts_service.TTSFn = Callable[[str, Voice], bytes]` (WAV 를 돌려줌)
  - `tts_service.default_tts(gemini_key: str, typecast_key: str) -> TTSFn` — provider 로 분기, `style="normal"`
  - `tts_service.synthesize_segment(text: str, voice: Voice, tts: TTSFn) -> bytes` — MP3. `TTSError` 면 1번 더, 그래도 실패면 `TTSError`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# test_audio.py — 1초 사인파 WAV 를 wave 모듈로 만들어 사용
def test_mp3_24k(): out = wav_to_mp3(wav_24k); out[:3] == b"ID3" or (out[0] == 0xFF and out[1] & 0xE0 == 0xE0); len(out) < len(wav_24k) / 4
def test_mp3_44k(): 44.1kHz 도 같은 조건

# test_tts_service.py — 가짜 TTSFn
def test_retry_once_then_ok(): 첫 호출 TTSError, 두 번째 WAV → MP3 반환, 호출 2번
def test_fail_twice_raises(): 두 번 모두 TTSError(status=429) → TTSError, 호출 2번
def test_browser_voice_not_called(): provider "browser" → ValueError, 호출 0번
```

- [ ] **Step 2: 실행해 실패 확인** — `uv run pytest tests/api -v`

- [ ] **Step 3: 구현** — `uv add lameenc`. `wave` 로 읽어 `lameenc.Encoder()` 에 비트레이트·샘플레이트·채널 1·quality 2 설정

- [ ] **Step 4: 통과 확인** — `uv run pytest -v`

- [ ] **Step 5: 커밋 (승인 후)** — `[기능] 구간 음성 생성과 MP3 변환 추가` (pyproject.toml·uv.lock 포함)

---

### Task 4: 이야기 API (처음 선택 후보, 시작, 다음 구간)

**Files:**
- Create: `app/story/start.py`, `app/api/log.py`, `app/main.py`
- Modify: `app/lab/api.py` (start-options·`segment_types` 를 `app/story/start.py` 에서 가져오게), `app/api/schemas.py`
- Test: `tests/api/test_story_api.py`

**Interfaces:**
- Consumes: Task 1~2 전부, `generate_segment`, `StoryContext`, `load_catalog`, `load_banned_words`
- Produces:
  - `start.segment_types(choice_count: int) -> list[str]`, `start.start_options(catalog: Catalog, rng: random.Random) -> dict` (실험 서버와 같은 형식: heroes 5, traits 4, backgrounds 4, objects 4)
  - `log.log_event(kind: str, **fields) -> None` — `logging.getLogger("story")` 로 `json.dumps({"kind": kind, **fields}, ensure_ascii=False)` 한 줄
  - `main.create_app(settings: Settings, primary: LLM, secondary: LLM | None, *, tts: TTSFn | None = None, limits: Limits | None = None, rng: random.Random | None = None) -> FastAPI` — `limits` 가 없으면 `Limits(settings.daily_stories_per_user, settings.daily_stories_total)`. 테스트는 미리 채운 `Limits` 를 넣는다
  - `main.build_app() -> FastAPI` — `Settings()` 와 `OpenAICompatClient` 로 조립 (실행: `uvicorn --factory app.main:build_app`)
  - 요청·응답 (`schemas.py`):
    - `StartRequest(anon_id: str (1~64자), cards: list[str] (3~5), choice_count: int = 4 (2~5))`
    - `NextRequest(anon_id: str, story: StoryKey, history: list[SignedSegment] (1개 이상), chosen: list[str])`
    - `SegmentResponse(story: StoryKey, index: int, segment: SignedSegment, done: bool)`
  - 엔드포인트:
    - `GET /api/start-options`
    - `POST /api/stories` → 카드 확인 → `try_start_story` → `pick_voice` → 발단 생성 → `SegmentResponse(index=0)`
    - `POST /api/stories/next` → 서명 확인 → 순서 확인 → 다음 구간 생성
  - 오류 응답 본문은 `{"detail": {"code": ...}}`: 400 `bad_cards`·`bad_signature`·`bad_order`·`bad_choice`, 409 `ended`, 429 `user_limit`·`total_limit`, 502 `generation_failed`

- [ ] **Step 1: 실패하는 테스트 작성** — `FakeLLM`, `segment_json`, `middles` 사용. 카드 `["rabbit", "rose", "star"]`, `choice_count=2`

```python
def test_start_options_shape(): heroes 5, traits 4, backgrounds 4, objects 4
def test_full_flow(): 시작 → index 0, type "intro", choices 3 → next(chosen=["dragon"]) → index 1 → next(chosen=["dragon","balloon"]) → type "ending", done True
def test_story_has_voice_and_id(): 응답 story.voice.provider == "gemini", story.id 가 비어 있지 않음
def test_bad_cards(): 없는 카드 또는 캐릭터 카드 없음 → 400 bad_cards, LLM 호출 0
def test_tampered_history(): history[0].segment.pages[0].text 수정 → 400 bad_signature, LLM 호출 0
def test_chosen_not_offered(): chosen=["unicorn"] → 400 bad_choice
def test_chosen_count_mismatch(): history 2개인데 chosen 1개 → 400 bad_order
def test_after_ending(): 결말까지 받은 history 로 next → 409 ended
def test_survives_restart(): 같은 settings 로 create_app 을 새로 만들어 next 요청 → 200
def test_user_limit_only_on_start(): per_user=1 → 두 번째 시작 429 user_limit, 첫 이야기 next 는 200
def test_generation_failed(): FakeLLM 이 LLMError 만 → 502 generation_failed, 로그에 attempts 포함 (caplog)
def test_log_has_no_secret(): caplog 전체에 story_secret·API 키 문자열이 없음
```

- [ ] **Step 2: 실행해 실패 확인** — `uv run pytest tests/api/test_story_api.py -v`

- [ ] **Step 3: 구현**
  - `StoryContext(cards, history=검증된 구간들, chosen, total_segments=choice_count + 1)`
  - 순서 규칙: `len(chosen) == len(history)`, `len(history) <= choice_count`, `chosen[i]` 는 `history[i].choices` 의 id 중 하나, 마지막 구간이 `ending` 이면 409
  - 생성: `generate_segment(..., version=settings.prompt_version, max_page_chars=settings.max_page_chars, lenient=True)`
  - 구간마다 `log_event("segment", story_id, index, type, model_used, latency_ms, attempts=[...], warnings=[...])`
  - 실험 서버의 start-options·`segment_types` 를 `app/story/start.py` 로 옮기고, 기존 `tests/test_lab_api.py` 가 그대로 통과하는지 확인

- [ ] **Step 4: 통과 확인** — `uv run pytest -v` 전체 PASS

- [ ] **Step 5: 커밋 (승인 후)** — `[기능] 저장 없는 이야기 생성 API 추가`

---

### Task 5: 음성·기록 API + 실행 연결

**Files:**
- Modify: `app/main.py`, `app/api/schemas.py`, `backend/.env.example`
- Test: `tests/api/test_tts_api.py`

**Interfaces:**
- Consumes: Task 1~4
- Produces:
  - `TTSRequest(story: StoryKey, index: int, segment: SignedSegment)` → `POST /api/tts` → `audio/mpeg`
    - 서명 확인(400 `bad_signature`) → `voice.provider == "browser"` 면 400 `browser_voice` → `allow_tts(story.id, index)` 아니면 429 `tts_limit` → 페이지 본문을 줄바꿈으로 이어 `synthesize_segment` → 실패 시 502 `tts_failed`
  - `EventRequest(anon_id: str, story_id: str | None = None, type: Literal["card_select","choice_time","drop_off","complete","replay","mute","error"], payload: dict = {})` → `POST /api/events` → 204, `log_event("client", ...)`. payload 를 JSON 으로 바꿔 2,000자 넘으면 413
  - CORS: `settings.cors_origins` 만 허용

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_tts_returns_mp3(): 시작 응답의 story·segment 로 /api/tts → 200, content-type audio/mpeg
def test_tts_tampered(): segment 본문 수정 → 400 bad_signature, TTS 호출 0
def test_tts_browser_voice(): story.voice 를 browser 로 바꾸면 서명이 깨지므로, 모든 Gemini·Typecast 한도를 미리 채운 앱에서 시작 → voice browser → /api/tts 400 browser_voice
def test_tts_third_call_limited(): 같은 index 세 번째 → 429 tts_limit
def test_tts_failed(): 가짜 TTS 가 항상 TTSError(429) → 502 tts_failed
def test_event_logged(): /api/events type "complete" → 204, caplog 에 kind "client"
def test_event_too_big(): payload 2,001자 → 413
def test_cors_allows_dev_origin(): Origin http://localhost:5173 preflight → access-control-allow-origin 일치
```

- [ ] **Step 2: 실행해 실패 확인** — `uv run pytest tests/api/test_tts_api.py -v`

- [ ] **Step 3: 구현** — `create_app` 에 엔드포인트·`CORSMiddleware` 추가. `.env.example` 에 서비스 설정 추가(값 비움): `PRIMARY_*`, `SECONDARY_*`, `PROMPT_VERSION=v8`, `STORY_SECRET`, `DAILY_STORIES_PER_USER=3`, `DAILY_STORIES_TOTAL=30`, `CORS_ORIGINS=["http://localhost:5173"]`. `GEMINI_API_KEY`·`TYPECAST_API_KEY` 는 기존 항목을 같이 씀

- [ ] **Step 4: 통과 확인** — `uv run pytest -v` 전체 PASS

- [ ] **Step 5: 커밋 (승인 후)** — `[기능] 구간 음성·사용 기록 API 추가`

---

### Task 6: 실제 키로 1편 확인 + 문서 (사용자와 함께)

**Files:**
- Modify: `CLAUDE.md`(실행 명령·진행 상황), `.claude/launch.json`(API 서버 항목)
- Create: `.claude/rules/api.md` (`paths: backend/app/api/**, backend/app/main.py`) — 저장 없는 구조·서명·한도 규칙과 '왜'

- [ ] **Step 1:** 사용자가 `.env` 에 `PRIMARY_*`·`STORY_SECRET` 을 채움 (값은 가려서 확인)
- [ ] **Step 2:** `uv run --env-file .env uvicorn --factory app.main:build_app --port 8000` 으로 실행 (실험 서버와 같은 포트를 쓰므로 둘 중 하나만 켬)
- [ ] **Step 3:** `/docs` 화면에서 시작 → 다음 → 결말까지 1편 생성, 발단 구간 `/api/tts` 1번 호출해 MP3 재생 확인. 걸린 시간·로그 줄을 사용자에게 보고
- [ ] **Step 4:** 문서 갱신 후 `[문서]` 커밋 (승인 후)

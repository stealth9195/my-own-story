# 1차: 이야기 생성 핵심 + 사전 실험 구현 계획

> **에이전트 작업자용:** 필수 하위 스킬: superpowers:subagent-driven-development(권장) 또는 superpowers:executing-plans로 Task 단위 실행. 단계는 체크박스(`- [ ]`)로 추적.

**목표:** 이야기 1구간을 생성·검증하는 백엔드 핵심 모듈을 만들고, 이 모듈로 무료 LLM·TTS를 비교 평가해 기본·예비 모델과 TTS 업체를 확정한다.

**구조:** 실험용 코드를 따로 버리지 않고, 실제 서비스가 쓸 `catalog`·`schema`·`validator`·`prompt`·`llm`·`generator` 모듈을 먼저 만든 뒤 평가 도구(`backend/eval/`)가 이 모듈을 그대로 사용한다. API 서버·DB·TTS 연동은 2차 계획에서 한다.

**기술 스택:** Python 3.12+, uv, pydantic 2, pydantic-settings, httpx, pytest

**기획안:** `docs/superpowers/specs/2026-10-28-my-own-story-design.md`

## 전체 계획 나누기

| 차수 | 범위 | 결과물 |
|---|---|---|
| **1차 (이 문서)** | 이야기 생성 핵심 모듈 + LLM 평가 도구 + TTS 확인 + 실험 실행 | 모델·TTS 확정, 평가 리포트 v1 |
| 2차 | FastAPI API + Supabase DB + TTS 연동 + 한도 관리 | 텍스트·음성 이야기 API |
| 3차 | React 기본 흐름 (카드 → 읽기 → 선택 → 결말) | 텍스트 동화 웹앱 |
| 4차 | 장면 조립 + 상태 효과 + 효과음·음악 + 에셋 제작 | 그림·소리 포함 |
| 5차 | 내 책장, 이어하기, 사용 기록, PWA, 배포, 비용 보호 | 공개 가능 상태 |

각 차수는 앞 차수가 끝난 뒤 별도 계획 문서로 작성한다.

## 전체 제약

- 운영비 0원. 무료 티어 API만 사용
- 대상 4~7세. 폭력·공포·죽음·차별 표현 금지, 따뜻한 결말
- 구간별 페이지 수: 도입 3(허용 2~4), 중간 3~4, 결말 4~5
- 페이지 본문: 2~3문장, 약 80~120자 요청. 검증 상한 250자
- 선택지: 중간·도입 구간은 3~4개, 결말은 없음. 선택지 ID는 `catalog.json`의 캐릭터·사물 ID만
- 선택 횟수: 설정값, 기본 4, 범위 2~5. 구간 = 도입 1 + 중간 (선택 횟수 - 1) + 결말 1, LLM 호출 = 선택 횟수 + 1
- LLM 실패 처리: 기본 모델 → 1회 재생성 → 예비 모델 1회 → 실패
- 모든 에셋 ID는 `catalog.json`에 있는 값만 허용. 없는 ID는 제거, 배경은 기본 배경으로 대체
- API 키는 `.env`에만 둔다. git에 올리지 않는다
- 커밋 메시지: `[유형] 제목` 한글 50자 이내, 본문 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. 사용자 승인 후 커밋
- 모든 명령은 `backend/` 폴더에서 실행

## 검토 중점

1. LLM 응답이 ```` ```json ```` 코드 블록이나 앞뒤 설명 문장으로 감싸져 옴 → 검증기가 JSON 부분만 꺼내 정상 처리 (Task 2)
2. 선택지 ID가 중복됨 → 중복 제거 후 3개 미만이면 실패 처리 (Task 2)
3. 본문이 빈 문자열이거나 한글이 전혀 없음(영어로 씀) → 실패 처리 후 재생성 (Task 2)
4. LLM API가 200을 주지만 내용이 비어 있음 → `LLMError`로 처리해 예비 모델로 넘어감 (Task 4)
5. 평가 실행 중 하루 한도에 걸려 중단됨 → 다시 실행하면 완료된 파일은 건너뛰고, 실패한 이야기는 `failed`로 기록하고 다음으로 진행 (Task 6)

---

## 파일 구조

```
.gitignore                        # 수정: .env, .venv, __pycache__, tts_out 추가
shared/catalog.json               # 에셋 목록 (최소 세트). 2차 이후 프론트도 사용
prompts/v1/system.md              # 이야기 생성 시스템 프롬프트 v1
prompt.md                         # 프롬프트 버전별 변경 기록
backend/
  pyproject.toml
  .env.example
  app/
    __init__.py
    config.py                     # 설정값
    catalog.py                    # catalog.json 로드·조회
    story/
      __init__.py
      schema.py                   # Segment 등 데이터 모델
      safety.py                   # 금지어 검사
      banned_words.txt
      validator.py                # LLM 출력 검증·정리
      prompt.py                   # 메시지 조립
      generator.py                # 재시도·예비 모델 전환
    llm/
      __init__.py
      client.py                   # OpenAI 호환 API 클라이언트
  eval/
    __init__.py
    cases.json                    # 고정 평가 케이스 10개
    models.example.json           # 평가 대상 모델 목록 예시
    judges.example.json           # 심사 모델 목록 예시
    judge_prompt.md               # 심사 기준
    story_runner.py               # 이야기 1편 끝까지 생성
    run_generate.py               # 모델별 생성 실행 (CLI)
    judge.py                      # 심사 메시지·응답 파싱
    run_judge.py                  # 심사 실행 (CLI)
    summarize.py                  # 결과 요약 표 (CLI)
    tts_check.py                  # TTS 비교 (CLI, 수동 확인)
  tests/
    conftest.py
    test_catalog.py
    test_validator.py
    test_prompt.py
    test_llm_client.py
    test_generator.py
    eval/test_story_runner.py
    eval/test_judge.py
    eval/test_summarize.py
docs/experiments/2026-llm-tts-results.md   # 실험 결과 (Task 9)
```

---

### Task 1: 백엔드 프로젝트 + 설정 + 에셋 목록

**파일:**
- 생성: `backend/pyproject.toml`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/catalog.py`, `shared/catalog.json`, `backend/tests/conftest.py`
- 수정: `.gitignore`
- 테스트: `backend/tests/test_catalog.py`

**인터페이스:**
- 제공:
  - `Settings` (pydantic-settings, `.env` 읽음): `choice_count: int = 4` (2~5 검증), `prompt_version: str = "v1"`, `max_page_chars: int = 250`, `primary_base_url: str`, `primary_api_key: str`, `primary_model: str`, `primary_json_mode: bool = True`, `secondary_base_url: str | None = None`, `secondary_api_key: str | None = None`, `secondary_model: str | None = None`, `secondary_json_mode: bool = True`
  - `PAGE_RANGES: dict[str, tuple[int, int]] = {"intro": (2, 4), "middle": (3, 4), "ending": (4, 5)}` (config.py)
  - `REPO_ROOT: Path` (config.py, 저장소 루트)
  - `Catalog` 모델 + `load_catalog(path: Path | None = None) -> Catalog` (기본값 `REPO_ROOT / "shared/catalog.json"`)
  - `Catalog.ids(kind: str) -> set[str]` (kind: `backgrounds`, `characters`, `objects`, `states`, `moods`, `sfx`, `times`)
  - `Catalog.choice_ids() -> set[str]` (캐릭터 ∪ 사물)
  - `Catalog.card_ids() -> list[str]`
  - `Catalog.name_of(asset_id: str) -> str`
  - `Catalog.prompt_listing() -> str` (종류별 한 줄: `characters: rabbit(토끼), bear(곰), ...`)
  - `Catalog.default_background`, `Catalog.default_state = "idle"`, `Catalog.default_mood = "calm"`

- [ ] **Step 1: 프로젝트 생성**

```bash
cd backend
uv init --app --no-readme --python 3.12
uv add pydantic pydantic-settings httpx
uv add --dev pytest
```
`pyproject.toml`에 `[tool.pytest.ini_options] testpaths = ["tests"]`, `pythonpath = ["."]` 추가. `uv init`이 만든 `main.py`는 삭제.

`.gitignore`에 추가: `.env`, `.venv/`, `__pycache__/`, `backend/eval/tts_out/`

`.env.example`: `Settings`의 모든 필드를 빈 값으로 나열 (`PRIMARY_BASE_URL=https://openrouter.ai/api/v1` 처럼 기본 주소만 예시로 채움. Gemini는 `https://generativelanguage.googleapis.com/v1beta/openai`)

- [ ] **Step 2: `shared/catalog.json` 작성 (최소 세트)**

형식:
```json
{
  "version": 1,
  "default_background": "meadow",
  "backgrounds": [{ "id": "meadow", "name": "풀밭", "tags": ["자연"] }],
  "times": [{ "id": "day", "name": "낮" }],
  "characters": [{ "id": "rabbit", "name": "토끼", "tags": ["동물"], "card": true }],
  "objects": [{ "id": "rose", "name": "장미", "tags": ["꽃"], "card": true }],
  "states": [{ "id": "idle", "name": "가만히" }],
  "moods": [{ "id": "calm", "name": "평화로움" }],
  "sfx": [{ "id": "magic_sparkle", "name": "마법 반짝" }],
  "bgm": [{ "id": "calm_loop", "name": "평화로운 음악", "mood": "calm" }]
}
```

항목:
- backgrounds(5): meadow 풀밭, forest 숲, sea 바다, castle 성, village 마을
- times(3): day 낮, night 밤, sunset 노을
- characters(10): rabbit 토끼, bear 곰, fox 여우, cat 고양이, puppy 강아지, dragon 아기 용, princess 공주, robot 로봇, owl 부엉이, dinosaur 공룡
- objects(10): rose 장미, star 별, cake 케이크, balloon 풍선, treasure_box 보물 상자, magic_wand 요술봉, rainbow 무지개, moon 달, ship 배, apple 사과
- card: true → rabbit, bear, cat, dragon, dinosaur, robot, rose, star, cake, rainbow (10개)
- states(8): idle 가만히, talking 말하기, sleeping 잠자기, happy 기쁨, surprised 놀람, scared 무서움, walking 걷기, thinking 생각하기
- moods(5): calm 평화로움, mystery 신비로움, exciting 신남, tense 살짝 긴장, warm 따뜻함
- sfx(10): magic_sparkle 마법 반짝, birds 새소리, wind 바람, footsteps 발소리, splash 물 첨벙, door_open 문 열림, laugh 웃음, bell 종소리, pop 뿅, snore 코 고는 소리
- bgm(3): calm_loop(calm), mystery_loop(mystery), exciting_loop(exciting)

- [ ] **Step 3: 실패하는 테스트 작성** (`tests/test_catalog.py`)

```python
def test_real_catalog_loads_and_ids_are_unique_across_kinds():
    cat = load_catalog()
    kinds = ["backgrounds", "characters", "objects", "states", "moods", "sfx", "times"]
    all_ids = [i for k in kinds for i in cat.ids(k)]
    assert len(all_ids) == len(set(all_ids))

def test_defaults_exist():
    cat = load_catalog()
    assert cat.default_background in cat.ids("backgrounds")
    assert "idle" in cat.ids("states")
    assert "calm" in cat.ids("moods")

def test_cards_are_choice_ids_and_at_least_10():
    cat = load_catalog()
    assert len(cat.card_ids()) >= 10
    assert set(cat.card_ids()) <= cat.choice_ids()

def test_bgm_mood_refers_to_existing_mood():
    cat = load_catalog()
    assert all(b.mood in cat.ids("moods") for b in cat.bgm)

def test_name_of_and_listing():
    cat = load_catalog()
    assert cat.name_of("rabbit") == "토끼"
    assert "rabbit(토끼)" in cat.prompt_listing()
```

- [ ] **Step 4: 실패 확인**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: FAIL (`ImportError`)

- [ ] **Step 5: `config.py`, `catalog.py` 구현**

`load_catalog`는 중복 ID가 있으면 `ValueError`. `name_of`는 없는 ID면 `KeyError`.

- [ ] **Step 6: 통과 확인**

Run: `uv run pytest -v`
Expected: 5 passed

- [ ] **Step 7: 커밋** — `[설정] 백엔드 프로젝트와 에셋 목록 추가`

---

### Task 2: 데이터 모델 + 금지어 + 검증기

**파일:**
- 생성: `backend/app/story/__init__.py`, `schema.py`, `safety.py`, `banned_words.txt`, `validator.py`
- 테스트: `backend/tests/test_validator.py`

**인터페이스:**
- 사용: `Catalog`, `PAGE_RANGES` (Task 1)
- 제공:
  - `SegmentType = Literal["intro", "middle", "ending"]`
  - `SceneCharacter(id: str, state: str = "idle")`, `Scene(background: str, time: str = "day", characters: list[SceneCharacter] = [], objects: list[str] = [])`, `Page(text: str, scene: Scene, mood: str = "calm", sfx: str | None = None)`, `Choice(id: str, label: str)`, `Segment(type: SegmentType, pages: list[Page], choices: list[Choice] = [])` (pydantic)
  - `load_banned_words(path: Path | None = None) -> list[str]`, `find_banned(text: str, banned: list[str]) -> list[str]`
  - `ValidationResult` (dataclass): `ok: bool`, `segment: Segment | None`, `errors: list[str]`, `dropped: list[str]`
  - `validate_segment(raw: str, segment_type: SegmentType, catalog: Catalog, banned: list[str], max_page_chars: int = 250) -> ValidationResult`

**검증 규칙** (순서대로)
1. `raw`에서 첫 `{`부터 마지막 `}`까지 꺼내 JSON 파싱. 실패 → `errors=["json"]`
2. `pages` 수가 `PAGE_RANGES[segment_type]` 밖 → `"page_count"`
3. 페이지 본문: 공백 제거 후 빈 문자열 → `"empty_text"`, 한글이 한 글자도 없음 → `"not_korean"`, `max_page_chars` 초과 → `"too_long"`
4. 장면: 없는 배경 → 기본 배경, 없는 시간대 → `day`, 없는 캐릭터·사물 ID → 제거, 없는 상태 → `idle`, 없는 분위기 → `calm`, 없는 효과음 → `None`. 제거·대체한 ID는 `dropped`에 기록 (실패 아님)
5. 선택지 (도입·중간): 없는 ID 제거, 중복 ID 제거, 4개 초과면 앞 4개만, 남은 수 3개 미만 → `"choices"`. 결말: 선택지가 있으면 버림 (실패 아님)
6. 본문·선택지 라벨에 금지어 → `"unsafe"`

`banned_words.txt` 초기 목록 (한 줄에 하나): 죽이, 죽었, 죽여, 피가, 피를, 살인, 시체, 자살, 칼로, 총으로, 때려, 저주, 지옥, 귀신, 바보, 멍청

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_validator.py`)

테스트용 정상 출력 생성 함수 `make_raw(type, pages=3, choices=["dragon","rose","star"])`를 테스트 파일 안에 둔다 (페이지 본문은 `"토끼가 숲에서 놀았어요."`).

```python
def test_valid_intro_passes(): ...  # ok True, len(pages)==3, len(choices)==3
def test_json_inside_code_fence_and_text():
    raw = "여기 있어요\n```json\n" + make_raw("intro") + "\n```"
    assert validate_segment(raw, "intro", cat, banned).ok
def test_broken_json_fails():  # errors == ["json"]
def test_page_count_out_of_range():  # middle with 2 pages → "page_count" in errors
def test_empty_text_fails():  # "empty_text"
def test_english_only_text_fails():  # text "The rabbit played." → "not_korean"
def test_too_long_text_fails():  # 251자 → "too_long"
def test_unknown_scene_ids_are_replaced_not_failed():
    # background "moon_base", character "alien", state "dancing", mood "spooky", sfx "boom"
    # → ok True, background == "meadow", characters == [], mood == "calm", sfx is None
    # → dropped contains "moon_base", "alien", "dancing", "spooky", "boom"
def test_duplicate_and_unknown_choices_removed_then_too_few_fails():
    # choices ["dragon", "dragon", "alien", "rose"] → 남은 2개 → "choices"
def test_more_than_four_choices_trimmed():  # 5개 정상 → 4개, ok True
def test_ending_choices_dropped():  # ending 4 pages + choices → ok True, choices == []
def test_banned_word_fails():  # "용이 기사를 죽였어요." → "unsafe"
```

- [ ] **Step 2: 실패 확인** — `uv run pytest tests/test_validator.py -v` → FAIL (`ImportError`)
- [ ] **Step 3: `schema.py`, `safety.py`, `banned_words.txt`, `validator.py` 구현** — 한글 판별은 `re.search(r"[가-힣]", text)`
- [ ] **Step 4: 통과 확인** — `uv run pytest -v` → 전부 PASS
- [ ] **Step 5: 커밋** — `[기능] 이야기 구간 데이터 모델과 출력 검증기 추가`

---

### Task 3: 프롬프트 v1 + 메시지 조립

**파일:**
- 생성: `prompts/v1/system.md`, `prompt.md`, `backend/app/story/prompt.py`
- 테스트: `backend/tests/test_prompt.py`

**인터페이스:**
- 사용: `Catalog`, `Segment`, `SegmentType`, `PAGE_RANGES`, `REPO_ROOT`
- 제공:
  - `StoryContext` (dataclass): `cards: list[str]` (에셋 ID), `history: list[Segment]`, `chosen: list[str]` (지금까지 고른 선택지 ID, 순서대로)
  - `build_messages(ctx: StoryContext, segment_type: SegmentType, catalog: Catalog, version: str = "v1") -> list[dict[str, str]]` → `[{"role": "system", ...}, {"role": "user", ...}]`
  - 프롬프트 파일 위치: `REPO_ROOT / "prompts" / version / "system.md"`. 없으면 `FileNotFoundError`

**`prompts/v1/system.md` 내용** (`{catalog}` 자리에 `catalog.prompt_listing()` 삽입)

```markdown
너는 4~7세 아이를 위한 한국어 동화 작가야. 아이가 고른 카드와 선택지로 이야기를 이어서 써.

## 글쓰기 규칙
- 한 페이지는 2~3문장, 80~120자. 쉬운 낱말, 짧은 문장, "~했어요" 말투
- 폭력, 공포, 죽음, 다툼, 차별, 나쁜 말 금지. 위험한 상황도 무섭지 않게
- 앞 내용과 자연스럽게 이어지게. 등장인물 이름과 성격 유지
- 결말이 아닌 구간의 마지막 페이지는 다음 선택이 궁금해지는 문장으로 끝내 (예: "그때 눈앞에 무언가 나타났어요. 그건 바로...")

## 선택지 규칙 (결말 제외)
- 3~4개. 각각: 아이가 고른 카드와 관련된 것 1개, 카드와 반대되는 것 1개, 엉뚱한 것 1개, 이야기 흐름에 잘 맞는 것 1개
- id는 아래 characters 또는 objects 목록의 id만. label은 아이가 읽을 짧은 이름

## 장면 규칙
- 모든 id는 아래 목록에 있는 것만 사용
- background 1개, time 1개, characters는 0~3개(각각 state 포함), objects 0~3개
- mood 1개, sfx는 어울리는 게 있을 때만 1개, 없으면 null

## 사용 가능한 목록
{catalog}

## 출력 형식
JSON만 출력. 설명 문장 금지.
{"pages":[{"text":"...","scene":{"background":"forest","time":"day","characters":[{"id":"rabbit","state":"happy"}],"objects":["rose"]},"mood":"calm","sfx":null}],"choices":[{"id":"dragon","label":"아기 용"}]}
```

**사용자 메시지 구성** (prompt.py에서 조립)
- 공통: `아이가 고른 카드: 토끼, 장미, 별` (이름으로)
- `history`가 있으면: `지금까지의 이야기:` + 모든 페이지 본문을 줄바꿈으로 연결
- `chosen`이 있으면: `아이가 방금 고른 선택지: 아기 용` (마지막 항목 이름)
- 구간별 지시
  - intro: `도입부를 3페이지로 써. 선택지 3~4개 포함.`
  - middle: `아이의 선택을 반영해서 이야기를 3~4페이지 이어 써. 선택지 3~4개 포함.`
  - ending: `아이의 선택을 반영해서 이야기를 4~5페이지로 따뜻하게 마무리해. 갑자기 끊기지 않게. "choices"는 빈 배열.`

**`prompt.md` 초기 내용:** 제목, v1 날짜(2026-10-28), "초기 버전. 기획안 규칙 그대로 반영", 점수 칸은 Task 9에서 채움

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_prompt.py`)

```python
def test_system_contains_catalog_listing():
    msgs = build_messages(StoryContext(cards=["rabbit","rose","star"], history=[], chosen=[]), "intro", cat)
    assert msgs[0]["role"] == "system" and "rabbit(토끼)" in msgs[0]["content"]
    assert "{catalog}" not in msgs[0]["content"]

def test_intro_user_message_has_card_names_and_no_history():
    # "토끼", "장미", "별" 포함, "지금까지의 이야기" 미포함, "3페이지" 포함

def test_middle_includes_history_and_last_choice_name():
    # history 1구간(본문 "토끼가 숲에 갔어요."), chosen ["dragon"]
    # → "토끼가 숲에 갔어요." 와 "아기 용" 포함, "3~4페이지" 포함

def test_ending_requests_empty_choices():
    # "빈 배열" 포함, "4~5페이지" 포함

def test_unknown_version_raises():
    with pytest.raises(FileNotFoundError):
        build_messages(ctx, "intro", cat, version="v999")
```

- [ ] **Step 2: 실패 확인** — `uv run pytest tests/test_prompt.py -v` → FAIL
- [ ] **Step 3: `system.md`, `prompt.py`, `prompt.md` 작성** — 템플릿 치환은 `str.replace("{catalog}", ...)` (JSON 예시의 중괄호 때문에 `str.format` 사용 금지)
- [ ] **Step 4: 통과 확인** — `uv run pytest -v` → 전부 PASS
- [ ] **Step 5: 커밋** — `[기능] 이야기 생성 프롬프트 v1과 메시지 조립 추가`

---

### Task 4: LLM 클라이언트

**파일:**
- 생성: `backend/app/llm/__init__.py`, `backend/app/llm/client.py`
- 테스트: `backend/tests/test_llm_client.py`

**인터페이스:**
- 제공:
  - `LLMResponse` (dataclass): `text: str`, `model: str`, `latency_ms: int`
  - `LLMError(Exception)`: `status: int | None` 속성
  - `OpenAICompatClient(base_url: str, api_key: str, model: str, json_mode: bool = True, timeout: float = 60.0, transport: httpx.BaseTransport | None = None)`
  - `OpenAICompatClient.model: str` (읽기용)
  - `OpenAICompatClient.complete(messages: list[dict[str, str]], temperature: float = 0.9) -> LLMResponse`
- 동작: `POST {base_url}/chat/completions`, 헤더 `Authorization: Bearer {api_key}`, 본문 `model`, `messages`, `temperature`, `json_mode`면 `response_format: {"type": "json_object"}`. 응답 `choices[0].message.content` 반환. OpenRouter·Gemini OpenAI 호환 주소 모두 이 형식

- [ ] **Step 1: 실패하는 테스트 작성** (`httpx.MockTransport` 사용)

```python
def test_sends_model_messages_and_json_mode(): ...
    # 요청 URL이 "https://x/v1/chat/completions", Authorization 헤더, body["response_format"] == {"type": "json_object"}
    # 반환 text == "{}", model == "m", latency_ms >= 0
def test_json_mode_off_omits_response_format(): ...
def test_non_200_raises_with_status():  # 429 → LLMError, status == 429
def test_network_error_raises():  # transport에서 httpx.ConnectError → LLMError, status is None
def test_empty_content_raises():  # content None 또는 "" → LLMError
```

- [ ] **Step 2: 실패 확인** — `uv run pytest tests/test_llm_client.py -v` → FAIL
- [ ] **Step 3: `client.py` 구현** — 동기 `httpx.Client`, 지연 시간은 `time.perf_counter()`
- [ ] **Step 4: 통과 확인** — `uv run pytest -v` → 전부 PASS
- [ ] **Step 5: 커밋** — `[기능] OpenAI 호환 LLM 클라이언트 추가`

---

### Task 5: 구간 생성기 (재시도·예비 모델)

**파일:**
- 생성: `backend/app/story/generator.py`
- 테스트: `backend/tests/test_generator.py`

**인터페이스:**
- 사용: `build_messages`, `StoryContext` (Task 3), `validate_segment` (Task 2), `LLMError`, `LLMResponse` (Task 4)
- 제공:
  - `LLM` (Protocol): `model: str`, `complete(messages, temperature=0.9) -> LLMResponse`
  - `Attempt` (dataclass): `model: str`, `ok: bool`, `errors: list[str]`, `latency_ms: int`
  - `GenerationResult` (dataclass): `segment: Segment`, `model_used: str`, `attempts: list[Attempt]`, `latency_ms: int` (모든 시도 합계)
  - `GenerationFailed(Exception)`: `attempts: list[Attempt]` 속성
  - `generate_segment(ctx: StoryContext, segment_type: SegmentType, *, primary: LLM, secondary: LLM | None, catalog: Catalog, banned: list[str], version: str = "v1", max_page_chars: int = 250) -> GenerationResult`
- 순서: 기본 1차 → (검증 실패 시) 기본 2차 → 예비 1회. 기본 모델에서 `LLMError`가 나면 재시도 없이 바로 예비로. `LLMError`도 `Attempt(ok=False, errors=["llm_error:{status}"])`로 기록

- [ ] **Step 1: 실패하는 테스트 작성** — 응답 목록을 차례로 돌려주는 `FakeLLM(model, responses: list[str | LLMError])`를 `tests/conftest.py`에 정의 (Task 6에서도 사용). `calls: int` 속성으로 호출 횟수 기록

```python
def test_first_try_valid():  # attempts 1개, model_used == "p"
def test_invalid_then_valid_retries_same_model():  # attempts 2개 모두 "p", 두 번째 ok
def test_invalid_twice_uses_secondary():  # attempts 3개, 마지막 model "s", model_used == "s"
def test_llm_error_skips_retry_and_uses_secondary():  # attempts 2개, 첫 errors == ["llm_error:429"]
def test_all_fail_raises_with_attempts():  # GenerationFailed, len(e.attempts) == 3
def test_no_secondary_fails_after_two():  # secondary None → GenerationFailed, attempts 2개
```

- [ ] **Step 2: 실패 확인** — `uv run pytest tests/test_generator.py -v` → FAIL
- [ ] **Step 3: `generator.py` 구현**
- [ ] **Step 4: 통과 확인** — `uv run pytest -v` → 전부 PASS
- [ ] **Step 5: 커밋** — `[기능] 재시도와 예비 모델 전환을 포함한 구간 생성기 추가`

---

### Task 6: 평가 도구 - 이야기 생성 실행

**파일:**
- 생성: `backend/eval/__init__.py`, `cases.json`, `models.example.json`, `story_runner.py`, `run_generate.py`
- 수정: `.gitignore` (`backend/eval/models.json`, `backend/eval/judges.json` 추가 — 개인 설정)
- 테스트: `backend/tests/eval/test_story_runner.py`

**인터페이스:**
- 사용: `generate_segment`, `GenerationFailed`, `StoryContext`, `OpenAICompatClient`, `load_catalog`, `load_banned_words`
- 제공:
  - `cases.json`: `[{"id": "c01", "cards": ["rabbit", "rose", "star"], "picks": [0, 1, 2, 3]}, ...]` 10개. `picks` 길이는 최대 선택 횟수(5)로 맞춰 둠. 카드는 3~5개, 서로 다른 조합. `picks[i]`는 i번째 선택에서 고를 선택지 순번 (선택지 수로 나눈 나머지 사용)
  - `models.example.json`: `[{"name": "gemma", "base_url": "...", "api_key_env": "GEMINI_API_KEY", "model": "<모델 ID>", "json_mode": true}]` — 실제 모델 ID는 사용자가 블로그 도구에서 쓰는 값으로 `models.json`에 작성
  - `run_story(case: dict, llm: LLM, catalog: Catalog, banned: list[str], choice_count: int, version: str) -> dict` 반환 형식:
    ```
    {"case_id", "model", "version", "status": "done" | "failed",
     "segments": [{"type", "pages", "choices", "chosen", "attempts": [Attempt as dict], "latency_ms"}],
     "failed_at": int | None}
    ```
    구간 순서: **intro 1 + middle (choice_count - 1) + ending 1**. 선택은 intro와 각 middle 끝에서 총 `choice_count`번. 실패하면 그 구간 번호를 `failed_at`에 넣고 중단 (예외를 밖으로 던지지 않음)
  - CLI: `uv run python -m eval.run_generate --models eval/models.json --out eval/results/<run_name> [--cases c01,c02]`
    - 저장: `<out>/<model name>/<case id>.json`
    - 이미 있는 파일 중 `status == "done"`은 건너뜀, `failed`는 다시 실행
    - `LLMError`로 한도 초과(429)가 연속 3번 나오면 그 모델은 중단하고 다음 모델로

- [ ] **Step 1: 실패하는 테스트 작성** (`FakeLLM`은 Task 5에서 만든 `tests/conftest.py` 것을 사용)

```python
def test_run_story_done_has_expected_segment_types():
    # choice_count=3 → types == ["intro", "middle", "middle", "ending"]
    # 각 비결말 구간에 chosen이 있고, chosen은 해당 구간 choices[picks[i] % len] 의 id
def test_run_story_failure_recorded_not_raised():
    # 두 번째 구간에서 모두 실패 → status "failed", failed_at == 1, segments 길이 1
def test_resume_skips_done_files(tmp_path):
    # done 파일이 있는 case는 FakeLLM 호출 0회. failed 파일은 다시 호출
```
마지막 테스트를 위해 `run_generate.py`에 `run_model(cases, llm, out_dir, ...) -> None` 함수를 두고 CLI는 이것을 호출만 한다.

- [ ] **Step 2: 실패 확인** — `uv run pytest tests/eval -v` → FAIL
- [ ] **Step 3: `story_runner.py`, `run_generate.py`, `cases.json`, `models.example.json` 작성**
- [ ] **Step 4: 통과 확인** — `uv run pytest -v` → 전부 PASS
- [ ] **Step 5: 커밋** — `[기능] 모델별 이야기 생성 평가 도구 추가`

> 구간 수 기준: 선택 횟수 N = 도입 끝 1번 + 중간 끝 (N-1)번. 구간은 N+1개, LLM 호출 N+1회. 기본 N=4 → 5구간.

---

### Task 7: 평가 도구 - 심사 + 요약

**파일:**
- 생성: `backend/eval/judge_prompt.md`, `judges.example.json`, `judge.py`, `run_judge.py`, `summarize.py`
- 테스트: `backend/tests/eval/test_judge.py`, `backend/tests/eval/test_summarize.py`

**인터페이스:**
- 제공:
  - `CRITERIA = ["length", "vocabulary", "plot", "coherence", "safety", "choices"]` (judge.py)
  - `story_to_text(story: dict) -> str` — 구간별 본문 + 선택지 목록 + 고른 선택지를 사람이 읽는 형태로
  - `build_judge_messages(story_text: str) -> list[dict[str, str]]`
  - `parse_judge(raw: str) -> dict[str, int]` — JSON 꺼내기(Task 2와 같은 방식), 6개 기준 모두 있고 1~5 정수여야 함, 아니면 `ValueError`
  - CLI `uv run python -m eval.run_judge --results eval/results/<run> --judges eval/judges.json` → `<run>/scores.jsonl`에 한 줄씩 `{"model", "case_id", "judge", "scores": {...}}`. 이미 있는 (model, case_id, judge) 조합은 건너뜀. `failed` 이야기는 심사 안 함
  - `summarize(run_dir: Path) -> str` (마크다운 표). CLI `uv run python -m eval.summarize eval/results/<run>` → 출력 + `<run>/summary.md` 저장
  - 표 열: 모델, 완료율, 첫 시도 성공률(전체 구간 중 attempts[0].ok 비율), 평균 구간 생성 시간(초), 기준별 평균, 총점(기준 평균의 합, 30점 만점)

**`judge_prompt.md` 기준** (각 1~5점, JSON만 출력)
- length: 페이지당 2~3문장, 전체 분량이 4~7세에 적당한가
- vocabulary: 4~7세가 이해할 낱말인가
- plot: 사건이 있고 재미있게 전개되는가
- coherence: 구간 사이, 선택지와 다음 내용이 자연스럽게 이어지는가. 결말이 갑자기 끊기지 않는가
- safety: 무섭거나 부적절한 내용이 없는가
- choices: 선택지가 다양하고(관련/반대/엉뚱/흐름) 아이가 고르고 싶게 만드는가

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_parse_judge_valid(): ...  # 코드 블록으로 감싼 6개 기준 → dict
def test_parse_judge_missing_key_raises(): ...
def test_parse_judge_out_of_range_raises(): ...  # 0 또는 6
def test_story_to_text_contains_pages_and_chosen(): ...
def test_summarize_table(tmp_path):
    # 모델 a: done 2개(첫 시도 성공 구간 7/8, latency 합 기반), 모델 b: done 1 + failed 1
    # scores.jsonl: a 두 이야기 각 judge 1명, 모든 기준 4점 → 총점 24.0
    # 결과 표에 "| a | 100% |", "| b | 50% |", "24.0" 포함
```

- [ ] **Step 2: 실패 확인** — `uv run pytest tests/eval -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** — `uv run pytest -v` → 전부 PASS
- [ ] **Step 5: 커밋** — `[기능] 이야기 심사와 결과 요약 도구 추가`

---

### Task 8: TTS 비교 스크립트

**파일:**
- 생성: `backend/eval/tts_check.py`
- 수정: `backend/.env.example` (`GOOGLE_TTS_API_KEY`, `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` 추가)

**인터페이스:**
- CLI: `uv run python -m eval.tts_check [--text "..."]` (기본 문장: 동화 2페이지 분량 약 200자, 스크립트에 고정)
- Google: `POST https://texttospeech.googleapis.com/v1/text:synthesize?key=...`, 목소리 후보 `ko-KR-Neural2-A`, `ko-KR-Wavenet-A`, `ko-KR-Standard-A`, mp3
- Azure: `POST https://{region}.tts.speech.microsoft.com/cognitiveservices/v1`, 헤더 `Ocp-Apim-Subscription-Key`, `X-Microsoft-OutputFormat: audio-24khz-48kbitrate-mono-mp3`, SSML 목소리 후보 `ko-KR-SunHiNeural`, `ko-KR-InJoonNeural`
- 출력: `backend/eval/tts_out/<업체>_<목소리>.mp3` + 표준 출력에 목소리별 응답 시간(ms)·파일 크기. 키가 없는 업체는 건너뛰고 안내 출력
- 자동 테스트 없음 (외부 API + 귀로 듣는 확인). 목소리 이름이 바뀌었으면 각 업체 목소리 목록 API로 확인 후 수정

- [ ] **Step 1: 스크립트 작성**
- [ ] **Step 2: 키 없이 실행해 건너뛰기 안내 확인** — `uv run python -m eval.tts_check` → "키 없음: google, azure 건너뜀" 형태 출력, 오류 없이 종료
- [ ] **Step 3: 커밋** — `[기능] TTS 업체 비교 스크립트 추가`

---

### Task 9: 실험 실행 + 결과 정리 (사용자와 함께)

API 키 발급과 결과 판단은 사용자가 한다. 키는 사용자가 직접 `.env`·`models.json`에 입력한다.

**파일:**
- 생성: `docs/experiments/2026-llm-tts-results.md`, `backend/eval/results/<run>/` (결과 파일, 커밋 대상 — 포트폴리오 근거)
- 수정: `prompt.md`, `docs/superpowers/specs/2026-10-28-my-own-story-design.md`

- [ ] **Step 1: 사용자가 키 준비** — OpenRouter, Google AI Studio(Gemini), Google Cloud TTS, Azure Speech. 각 무료 한도를 발급 화면에서 확인해 결과 문서에 기록
- [ ] **Step 2: 1개 케이스로 시험 실행** — `uv run python -m eval.run_generate --models eval/models.json --out eval/results/run1 --cases c01` → 모델별 `c01.json` 생성 확인. `not_korean`, `json` 오류가 많은 모델은 `json_mode` 설정 확인
- [ ] **Step 3: 전체 실행** (한도에 걸리면 다음 날 같은 명령 재실행) — 모델 3개 × 10편
- [ ] **Step 4: 심사 + 요약** — (변경: API 심사 대신 수동 심사) `uv run python -m eval.export eval/results/<run>` → `export/s*.md`와 `평가질문.md`를 ChatGPT·Gemini·Claude에 첨부 → 답변 CSV를 `export/scores/<챗봇>.csv`로 저장 → `uv run python -m eval.summarize eval/results/<run>`
- [ ] **Step 5: 사람 확인** — 모델별 2편씩 직접 읽고 심사 점수와 맞는지 메모
- [ ] **Step 6: TTS 비교** — `tts_check` 실행 후 사용자가 듣고 목소리 선택
- [ ] **Step 7: 결과 문서 작성** — 요약 표, 한도, 선택한 기본·예비 LLM과 TTS, 이유, 문제·해결 기록
- [ ] **Step 8: 기획안 갱신** — 16장 미정 항목 중 LLM·TTS 확정, `prompt.md`에 v1 점수 기록
- [ ] **Step 9: 커밋** — `[문서] LLM·TTS 사전 실험 결과 정리`

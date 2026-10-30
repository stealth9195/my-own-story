# 배포 안내

프론트는 **Cloudflare Pages**, 백엔드는 **Render 무료**에 올린다. 둘 다 카드 등록 없이 무료.
Cloud Run 은 카드 등록·과금 위험 때문에 쓰지 않는다(2026-10-29).

## 순서

1. **GitHub 에 올리기**: 저장소 `stealth9195/my-own-story` 에 브랜치를 push 한다.
   - 올리기 전에 비밀 값 검사(아래 '비밀 값')를 한다.
2. **Render (백엔드)**
   1. Render → New → **Blueprint** → 저장소 선택. 저장소 맨 위의 `render.yaml` 을 읽어 서비스 `my-own-story-api` 를 만든다.
   2. `sync: false` 로 적힌 환경 변수를 Render 화면에서 넣는다(아래 표). `CORS_ORIGINS` 는 Pages 주소를 아직 모르면 일단 `'["http://localhost:5173"]'`.
   3. 배포가 끝나면 `https://<서비스 이름>.onrender.com/api/start-options` 를 열어 JSON 이 나오는지 본다.
3. **Cloudflare Pages (프론트)**
   1. Workers & Pages → Create → Pages → 저장소 연결.
   2. Root directory `frontend`, Build command `npm ci && npm run build`, Output `dist`.
   3. 환경 변수 `VITE_API_BASE` = Render 주소(끝에 `/` 없이). 예시는 `frontend/.env.production.example`.
4. **CORS 맞추기**: Render 의 `CORS_ORIGINS` 에 Pages 주소를 넣고 다시 배포한다.
   - 예: `'["https://my-own-story.pages.dev"]'` (JSON 목록, 작은따옴표로 감쌈)
5. **확인**: 배포 주소로 PC 에서 1편 끝까지, 휴대폰에서 홈 화면에 추가·소리·이어하기.

## 환경 변수 (Render)

| 이름 | 예시·설명 |
|---|---|
| `PYTHON_VERSION` | `3.12` (render.yaml 에 고정) |
| `PROMPT_VERSION` | `v9` (render.yaml 에 고정) |
| `GEMINI_API_KEY` | Google AI Studio 키. 이야기 생성·이야기 음성 모두 |
| `STORY_SECRET` | 구간 서명 비밀값, 32자 이상. `uv run python -c "import secrets;print(secrets.token_hex(32))"` 로 만든다. 로컬 `.env` 와 다른 값을 쓴다 |
| `PRIMARY_MODEL` / `SECONDARY_MODEL` | 로컬 `.env` 와 같은 이야기 생성 모델 |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` | 안내·선택지 목소리(무료 F0). 비우면 브라우저 음성 |
| `TYPECAST_API_KEY` | 예비 TTS. 비워도 된다 |
| `CORS_ORIGINS` | 허용할 프론트 주소 JSON 목록 |

그 밖의 값(하루 한도 등)은 코드 기본값을 쓴다(`backend/app/config.py`).

## 무료 요금제 한계

- **Render 잠듦**: 15분 동안 요청이 없으면 잠들고, 깨는 데 약 1분 걸린다.
  - 홈 화면이 뜨면 `/api/start-options` 를 한 번 불러 미리 깨운다(`wakeServer`). 처음 선택 후보는 70초까지 기다린다.
  - **시연 전에는 배포 주소를 미리 한 번 열어 둔다.**
- **메모리 한도 초기화**: 하루 이야기 수·TTS 사용량은 서버 메모리에서 센다. 잠들거나 다시 배포하면 0부터 센다.
  - 실제 한도는 Google 이 막으므로 넘쳐도 과금은 없고, 그 구간이 글만 나온다.
- **Gemini TTS**: 모델마다 하루 10회, 태평양 시간 자정(한국 16~17시)에 다시 찬다. 하루에 들을 수 있는 이야기 수가 적다.
- **기록**: 서버 기록(`story_start`·`tts`·`tts_failed` 등)은 Render 화면의 Logs 에서 본다. 파일로는 남지 않는다.

## 비밀 값

- `.env`·`backend/eval/models.json`·개인 메모는 git 에서 뺀다(`.gitignore`).
- 첫 push 전에 확인:
  ```bat
  git ls-files | findstr /i ".env models.json"
  git grep -nE "AIza[0-9A-Za-z_-]{20,}|sk-or-"
  ```
  첫 줄은 `.env.example`·`.env.experiment`·`.env.production.example` 만 나와야 하고, 둘째 줄은 아무것도 나오지 않아야 한다.
- 키는 Render·Cloudflare 화면에만 넣는다. 키를 잘못 올렸으면 저장소에서 지우는 것으로는 부족하다 → 그 키를 폐기하고 새로 만든다.

## 업데이트

- push 하면 Render·Pages 가 자동으로 다시 배포한다.
- 휴대폰에 설치한 앱(PWA)은 다음에 열 때 새 버전으로 바뀐다(자동 업데이트).

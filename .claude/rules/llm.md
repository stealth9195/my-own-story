---
paths:
  - "backend/app/llm/**"
  - "backend/app/tts/**"
  - "backend/app/story/generator.py"
  - "backend/app/config.py"
  - "backend/.env.example"
  - "backend/eval/run_generate.py"
  - "backend/eval/tts_check.py"
  - "backend/eval/models.example.json"
---
# LLM·TTS 호출 규칙 (무료 한도 있음)

- 실제 호출은 **꼭 필요할 때만**(모델 비교, 프롬프트 새 버전 확인). 나머지는 가짜 응답으로 검증한다.
- 클라이언트는 OpenAI 호환 형식 하나로 Gemini·OpenRouter 를 모두 부른다(`PRIMARY_*`, `SECONDARY_*` 의 주소·키·모델만 바꿈).
- 생성 순서(`generator.py`): 기본 모델 → 검증 실패면 기본 모델 1번 더 → 예비 모델 1번.
  기본 모델에서 `LLMError` 가 나면 **오류 종류와 상관없이** 바로 예비 모델로 넘어간다.
  - 왜: 아이가 듣는 중에 이야기가 끊기지 않는 쪽을 택했다. 대신 키·설정 오류가 숨을 수 있으니
    모든 시도를 `attempts`(모델·성공 여부·오류·걸린 시간)에 남기고, 실패하면 `GenerationFailed` 로 전부 드러낸다.
- 출력은 JSON 모드(`response_format: json_object`) + `validator.py` 검증으로 강제한다. 목록 밖 ID 는 검증에서 걸러진다.
- 모델별 추가 요청 옵션(추론 끄기 등)과 응답 대기 시간은 `eval/models.json` 에서 모델마다 지정한다(키는 넣지 않음, git 제외).
- TTS 응답 형식은 모델마다 다르다: 2.5 는 순수 PCM(`audio/L16;rate=24000`), 3.8 은 WAV 통째(`audio/wav`, 끝에 C2PA·IPTC 출처 표시 약 6KB). `mimeType`·`RIFF` 로 구분해 소리 부분만 쓴다(`gemini.py` 의 `_to_wav`).
  - 겪은 버그: WAV 를 PCM 으로 보고 다시 감싸 시작 잡음·끝 '콱' 소리(2026-10-30). 새 모델을 추가하면 응답 `mimeType` 을 한 번 확인한다.
- 호출 기록: 로컬은 `backend/logs/날짜.log` 에 시각과 함께 남는다(`segment`·`segment_unused`·`tts_failed` 등에 모델·성공·걸린 시간). 토큰 수는 아직 없음. 배포는 Render Logs.

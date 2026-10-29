---
paths:
  - "prompts/**"
  - "backend/app/story/**"
  - "backend/app/catalog.py"
  - "shared/catalog.json"
  - "backend/eval/judge.py"
  - "backend/eval/judge_prompt.md"
  - "backend/eval/cases.json"
---
# 이야기 생성·안전 규칙

## 프롬프트 버전
- 새 버전은 `prompts/vN/system.md` 폴더를 새로 만든다. **이전 버전 파일은 고치지 않는다.**
  - 왜: 모델 평가 결과를 버전끼리 비교해야 하고, 그 비교가 발표의 수치 전후 근거가 된다.
- 사용할 버전은 `.env` 의 `PROMPT_VERSION`, 평가 스크립트는 `--version` 으로 고른다. 코드 기본값(`run_generate` v1)은 최신이 아니다.

## 에셋 목록
- `shared/catalog.json` 은 프론트와 백엔드가 같이 쓴다. 그림·효과음·음악 ID 는 여기 있는 값만 허용한다.
- 그림·소리 매칭에 임베딩을 쓰지 않는다. 프롬프트에 목록을 넣고 ID 만 고르게 한다.

## 아이용 안전
- 4~7세 대상. 무섭거나 폭력적인 표현은 `banned_words.txt`·`safety.py` 로 걸러낸다.
- `validator.py` 가 형식·없는 ID·금지어·분량·선택지 규칙을 검사한다. 실패하면 생성기가 재시도한다(`rules/llm.md`).
- 선택지 규칙(v2~): 이미 나온 선택지·카드를 다시 내지 않고, 고르지 않은 선택지가 이후 장면에 나오지 않게 한다.

## 평가 기준
- `eval/judge.py` 의 `CRITERIA` 배점(합계 100)은 `judge_prompt.md` 와 **같은 값이어야 한다.** 한쪽을 바꾸면 다른 쪽도 바꾼다.

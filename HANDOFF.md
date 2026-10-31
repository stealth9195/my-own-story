# HANDOFF — 다음 세션 시작 안내

갱신: 2026-10-31 · 5차 디자인 개편 끝, master 에 합치고 push·배포함(마지막 `3bf0448`) · 원격 `origin` = https://github.com/stealth9195/my-own-story

**배포 주소**: 앱 https://my-own-story.pages.dev (Cloudflare Pages) · API https://my-own-story-api.onrender.com (Render 무료). master 에 push 하면 둘 다 다시 배포된다(`docs/deploy.md`).

## 다음에 할 일 (사용자가 정한 순서)

1. **프롬프트 v1~v9 결과 품질 평가·비교** — 정해 둔 기준(`eval/judge.py` 의 `CRITERIA`, `judge_prompt.md`)으로 점수를 매겨 발표용 전후 비교
2. 기획안(PRD)과 실제 결과물 비교 (`prd-match-report`, 본문은 고치지 않음)
3. 3.8 TTS 용 지시 형식 시험(B) — 무료 TTS 한도를 쓰므로 시연 뒤 추천
- 마감: **2026-11-03(화) 발표, 시연은 PC.** 11/1(일) 작업 불가, 11/2(월) 저녁 불가

## 시작 전에 확인할 것

1. 커밋: 메시지를 먼저 보여 주고 승인 후 커밋(`commit-with-design-notes`). push 는 사용자 요청 때만
2. **방금 배포한 것 확인 안 된 부분**(사용자에게 물어볼 것)
   - Render 대시보드 Events 맨 위가 `3bf0448` 'Deploy live' 인지(API 응답만으로는 새 코드인지 알 수 없음)
   - 휴대폰에서 하얗게 멈췄던 이야기(쪽 0개 구간 저장됨)는 책장에서 지우기. 다시 멈추면 콘솔 메시지·시각을 받아 Render Logs 의 `segment` 기록(`page_count`, `hero_added`) 확인
3. 시연은 PC(노트북·프로젝터) → PC(≥1024px) 화면 우선, 폰은 큰 오류만. 아이폰 음량 문제는 고치지 않기로 함
4. 시연용 ElevenLabs 목소리: 유료 크레딧, 설정 창에서 고른 사람만. 시연이 끝나면 Render 의 `ELEVENLABS_API_KEY` 를 지운다
5. 시연 전: 배포 주소를 미리 열어 Render 를 깨운다. Gemini TTS 는 모델당 하루 10회라 리허설로 다 쓰지 않게. 글꼴(Jua·Pretendard)을 인터넷에서 불러오므로 시연 장소 인터넷 확인. 설치한 PWA 는 껐다 켜야 새 버전

## 2026-10-31 이번 세션 한 일

- **디자인 시안**: OpenDesign(이 PC 의 Claude Code 로 실행, OpenDesign Cloud 는 로그인 필요해 안 씀)으로 스타일 타일 2안 → **A안 '크레파스 손그림 + 그림책'** 선택 → 모든 화면 시안(PC 1440×900·1280×720, 폰 375).
  시안 프로젝트는 로컬 OpenDesign `my-own-story-0b26`(공통 CSS `screens/a-tokens.css`)
- **앱 적용**(워크트리 `experiment/redesign` 에서 화면 단위로 확인·커밋 후 master 에 fast-forward, 워크트리·브랜치 정리함)
  - 공통 색·글꼴·버튼(`index.css`), 모든 화면 PC 펼친 그림책 배치: 홈·처음 선택·기다림(고른 카드가 책 속으로)·읽기·책장·설정·오류
  - PC 읽기 화면 책장 넘김: 다음 = 오른쪽 글 쪽이 왼쪽으로, 이전(다시 듣기 ◀) = 왼쪽 장면 쪽이 오른쪽으로
  - 책장: 두께 있는 책(종이는 줄 없음, 비교 후 결정)이 꽂힌 크레파스 책장, 책을 누르면 창(다시 듣기=바로 처음부터 / 이어하기 / 지우기·한 번 더 확인), 표지 왼쪽 위 하트(좋아하는 이야기)
  - 새 이야기 1편을 처음 선택부터 결말까지 실제로 진행해 확인
- **버그 수정**
  - 다시 듣기에서 '다음'을 누르면 넘김이 두 번: MP3 위치 이동이 살짝 앞에 멈춰 쪽이 2→1→2 로 되돌아감 → 0.05초 뒤로, 길이 알기 전·이동 중 위치 알림 무시
  - 배포판에서 읽기 화면이 하얗게 멈춤(`undefined 'scene'`): 서버의 느슨한 검사가 쪽 0개 구간을 통과시킴 → 서버 거절(`no_pages`), 화면은 쪽이 없으면 오류 화면
- **결말 주인공**: 결말 장면에 처음 고른 주인공이 빠지면 서버가 서명 전에 넣음(`story/hero.py`, LLM 재호출 없음, 프롬프트 버전 그대로)
- 테스트: 프론트 73개, 백엔드 324개 통과. 문서는 `CLAUDE.md`·`.claude/rules/frontend.md`·`story.md` 에 반영

## 실행

```bat
:: 백엔드 (backend 폴더) — .env 에 GEMINI_API_KEY, STORY_SECRET, PRIMARY_MODEL, SECONDARY_MODEL, AZURE_SPEECH_KEY/REGION, PROMPT_VERSION=v9
uv run --env-file .env uvicorn --factory app.main:build_app --port 8001
uv run pytest

:: 프론트 (frontend 폴더) — /api 는 Vite 프록시로 8001 에 넘어감(API 서버를 같이 켜야 이야기를 만들 수 있음)
npm run dev
npm test
npm run build
```

`.claude/launch.json`: `story-api`(8001), `story-web`(5173), `story-lab`(8000), `story-web-build`(4173, 빌드 미리보기).
개발 확인 화면(서버 없이): `?demo`(링크 모음), `?demo=reading`·`reading-phrase`·`reading-turn`(책장 넘김 3쪽), `?demo=waiting`, `?demo=problem`·`problem-limit`.

## 사용자 작업 스타일 (꼭 지킬 것)

- **한국어로 답한다**(고유명사 빼고). 짧게, 고른 대로 고쳤으면 수정 내역을 다시 풀어 쓰지 않는다
- 정해지지 않은 것은 선택지(장단점·예시)로 묻는다. 의견을 물으면 코드는 고치지 않고 의견만
- 큰 화면 변경·실험은 워크트리(`../my-own-story-<이름>`, 다른 포트)에서 보여 주고 승인 후 합친다. 작은 수정은 master 에서
- push·저장소·master 합치기·배포 연결은 사용자 요청/승인 후에만
- 사용자는 React 처음 → 처음 나오는 개념에 짧은 주석
- 화면은 직접 브라우저로 확인하고(PC 1440·1280, 폰 375) 결과를 말한다. 이미 잘 된 것까지 다시 돌리지 않는다

## 알아 둘 함정

- 무료 한도: Gemini TTS 모델당 하루 10회·분당 3회(태평양 자정 초기화). 서버 한도 계산은 메모리라 다시 켜면 0부터
- 배포판 오류 위치: 콘솔의 `index-xxxx.js:줄:칸` 을 배포 주소 `/assets/` 파일에서 그 칸 앞뒤로 잘라 본다(소스맵 없음)
- CSS 는 전역이라 다른 화면과 클래스 이름이 겹치면 깨진다(홈의 `.actor` 가 장면 `.actor` 와 겹쳤음) → 화면 접두어 사용
- PC 화면 조건은 `@media (min-width: 1024px)`, 폰 가로는 `(orientation: landscape) and (max-width: 1023px)` — PC 도 가로라 범위를 꼭 나눈다
- 미리보기 창(브라우저 패널)의 화면 크기 설정은 턴이 끝나면 풀린다 → PC 확인 결과가 폰 배치로 나올 수 있음. 패널이 숨겨지면 애니메이션·rAF 가 멈춘다
- 개발용 `?demo=reading` 에서 선택지를 두 번 누르면 가짜 이야기(1970년 날짜)가 책장에 저장된다 → 이어하기 시 서버가 서명을 거절(정상), 책장에서 지우면 됨
- 3.x TTS 모델은 한 문장짜리 지시를 소리 내어 읽었다 → `DIRECTOR'S NOTES / TRANSCRIPT` 형식으로 해결
- `uv run --env-file` 은 큰따옴표를 지운다 → `.env` 의 JSON 목록은 작은따옴표로
- React StrictMode 는 개발 중 useEffect 를 두 번 실행 → 서버 요청 중복은 `audioRequests`·`requesting` 으로 막음
- Windows 콘솔에서 한글이 깨져 보인다(cp949). 콘솔 출력이 필요하면 UTF-8 로 파일에 써서 본다

## 남은 문제

`CLAUDE.md` 의 진행 상황 '남은 문제' 참고. 이번에 추가된 것:
- 글꼴을 인터넷에서 불러옴(끊기면 기본 글꼴) → 필요하면 글꼴 파일을 앱에 넣기
- PWA 설치 색(`vite.config.ts` 의 `theme_color`·`background_color`)이 예전 주황·크림 그대로
- PC 책장 넘김은 실제 생성 중 구간 전환에서 3번 중 2번만 기록으로 확인 → 시연 PC 에서 한 번 더
- 결말 주인공 채우기·쪽 0개 거절은 실제 사례(LLM 이 빼먹은 경우)로는 아직 못 봄 → Render Logs 의 `hero_added`, `segment_failed`/`no_pages` 로 확인

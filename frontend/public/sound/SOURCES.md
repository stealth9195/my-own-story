# 소리 파일 출처

## 효과음 (`sound/`)

모두 [Pixabay](https://pixabay.com/sound-effects/) 에서 받음 (Pixabay Content License: 상업 이용 가능, 출처 표기 불필요).

bell, birds, door_open, footsteps, laugh, magic_sparkle, pop, snore, splash, wind

## 배경 음악 (`bgm/`)

모두 [ElevenLabs](https://elevenlabs.io/) 음악 생성으로 직접 만듦 (유료 구독 중 생성·다운로드).

| 파일 | 분위기 |
|---|---|
| calm_loop | 평화로움 (calm) |
| mystery_loop | 신비로움 (mystery) |
| exciting_loop | 신남 (exciting) |
| tense | 살짝 긴장 (tense) |
| warm | 따뜻함 (warm) |
| ending | 결말 (ending) |

곡을 더 넣으려면: 파일을 `bgm/{id}.mp3` 로 두고 `shared/catalog.json` 의 `bgm` 에 `{id, name, mood}` 를 추가한다. 같은 분위기 곡이 여럿이면 이야기마다 하나를 고른다.

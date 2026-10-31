// 개발용 확인 화면. npm run dev 에서 주소 끝에 ?demo 를 붙이면 열린다(배포판에서는 꺼짐).
// 서버·저장소 없이 예시 장면(사물 위치 켜기/끄기)과 읽기 화면(?demo=reading, ?demo=reading-phrase)을 보여 준다
import { useState } from "react";
import type { Choice, Page } from "./api";
import Scene from "./components/Scene";
import Problem from "./screens/Problem";
import Reading from "./screens/Reading";
import Waiting from "./screens/Waiting";
import type { SavedStory } from "./storage";

const scene = (background: string, time: string, characters: [string, string][], objects: string[]): Page["scene"] =>
  ({ background, time, characters: characters.map(([id, state]) => ({ id, state })), objects });

const SAMPLES: { title: string; scene: Page["scene"] }[] = [
  { title: "공주가 왕관을 썼어요", scene: scene("castle", "day", [["princess", "happy"]], ["crown"]) },
  { title: "마법사가 요술봉을 들었어요", scene: scene("forest", "day", [["wizard", "talking"], ["rabbit", "surprised"]], ["magic_wand"]) },
  { title: "곰과 여우, 왕관과 꽃 왕관", scene: scene("meadow", "day", [["bear", "happy"], ["fox", "happy"]], ["crown", "flower_crown"]) },
  { title: "부엉이가 등불을 들고 밤길을", scene: scene("forest", "night", [["owl", "walking"]], ["lantern", "moon"]) },
  { title: "토끼가 풍선을, 하늘엔 무지개", scene: scene("meadow", "day", [["rabbit", "happy"], ["puppy", "idle"]], ["balloon", "rainbow"]) },
  { title: "기린이 열쇠를 찾았어요 (머리 높은 캐릭터)", scene: scene("village", "sunset", [["giraffe", "surprised"]], ["key", "crown"]) },
  { title: "거북이와 보물 상자 (바닥 사물)", scene: scene("sea", "day", [["turtle", "thinking"]], ["treasure_box", "star"]) },
];

// 읽기 화면 확인용 가짜 이야기 (저장소·서버 없이 선택지 화면부터 보여 준다)
const ITEM_CHOICES: Choice[] = [
  { kind: "item", id: "key", label: "열쇠" }, { kind: "item", id: "map", label: "지도" }, { kind: "item", id: "lantern", label: "등불" },
];
const PHRASE_CHOICES: Choice[] = [
  { kind: "phrase", id: "p1", label: "여우에게 인사를 건넨다" }, { kind: "phrase", id: "p2", label: "조용히 숲속으로 들어간다" },
  { kind: "phrase", id: "p3", label: "부엉이에게 길을 묻는다" }, { kind: "phrase", id: "p4", label: "곰을 깨워서 함께 간다" },
];

function sampleStory(phrases: boolean): SavedStory {
  return {
    story: { id: "demo-reading", cards: ["fox", "forest"], choice_count: 4, voice: { provider: "browser" } } as SavedStory["story"],
    segments: [{ sig: "demo", segment: { type: "intro", choices: phrases ? PHRASE_CHOICES : ITEM_CHOICES, pages: [{
      text: "여우와 친구들이 숲속에서 만났어요. 모두 함께 반짝이는 열쇠를 찾으러 떠났어요. 길은 멀었지만 모두 신이 났어요.",
      scene: scene("forest", "day", [["fox", "talking"], ["owl", "happy"], ["bear", "sleeping"]], ["key", "crown"]),
      mood: "calm", sfx: null,
    }] } }],
    chosen: [], createdAt: 0, done: false,
  };
}

// 책장 넘김 확인용: 장면이 다른 3쪽. 브라우저 음성으로 쪽이 차례로 넘어간다
function turnStory(): SavedStory {
  const s = sampleStory(false);
  const page = (text: string, sc: Page["scene"]) => ({ text, scene: sc, mood: "calm", sfx: null });
  s.story.id = "demo-turn";
  s.segments[0].segment.pages = [
    page("곰돌이가 숲속을 걷고 있었어요.", scene("forest", "day", [["bear", "walking"]], [])),
    page("여우가 반짝이는 보물상자를 찾았어요.", scene("forest", "day", [["fox", "surprised"]], ["treasure_box"])),
    page("토끼도 달려와서 함께 웃었어요.", scene("meadow", "sunset", [["rabbit", "happy"], ["fox", "happy"]], [])),
  ] as Page[];
  return s;
}

export default function Demo() {
  // ?demo=reading (그림 선택지) / ?demo=reading-phrase (문장 선택지): 읽기 화면을 바로 띄운다
  const mode = new URLSearchParams(location.search).get("demo");
  if (mode === "reading" || mode === "reading-phrase") {
    return <Reading saved={sampleStory(mode === "reading-phrase")} resume onUpdate={() => {}}
                    onHome={() => { location.search = "?demo"; }} onNew={() => {}} />;
  }
  // ?demo=reading-turn: 3쪽을 차례로 읽으며 PC 책장 넘김 확인
  if (mode === "reading-turn") {
    return <Reading saved={turnStory()} onUpdate={() => {}} onHome={() => { location.search = "?demo"; }} onNew={() => {}} />;
  }
  // ?demo=problem (다시 할 수 있는 오류) / ?demo=problem-limit (하루 한도): 오류 화면
  if (mode === "problem" || mode === "problem-limit") {
    return <Problem code={mode === "problem" ? "unknown" : "user_limit"} onRetry={() => {}} onHome={() => { location.search = "?demo"; }} />;
  }
  // ?demo=waiting: 기다림 화면 (이야기를 만들지 않고 고른 카드 애니메이션만)
  if (mode === "waiting") return <Waiting cards={["bear", "kind", "forest", "treasure_box"]} />;
  return <SceneCompare />;
}

function SceneCompare() {
  // useState: 토글 값. 바뀌면 모든 장면을 다시 그린다
  const [placed, setPlaced] = useState(true);
  return (
    <main style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: 16 }}>
      <label style={{ fontSize: 20, fontWeight: 700, display: "flex", gap: 8, alignItems: "center" }}>
        <input type="checkbox" checked={placed} onChange={(e) => setPlaced(e.target.checked)} style={{ width: 24, height: 24 }} />
        사물 위치 정보 {placed ? "켜짐 (머리·손·하늘)" : "꺼짐 (캐릭터처럼 바닥)"}
      </label>
      <p style={{ margin: 0, display: "flex", gap: 16 }}>
        <a href="?demo=reading">읽기 화면 (그림 선택지)</a>
        <a href="?demo=reading-phrase">읽기 화면 (문장 선택지)</a>
        <a href="?demo=reading-turn">책장 넘김 (3쪽)</a>
        <a href="?demo=waiting">기다림 화면</a>
        <a href="?demo=problem">오류 화면</a>
      </p>
      {SAMPLES.map((s) => (
        <section key={s.title} style={{ width: "100%", maxWidth: 780 }}>
          <p style={{ margin: "0 0 6px" }}>{s.title}</p>
          <Scene scene={s.scene} placed={placed} />
        </section>
      ))}
    </main>
  );
}

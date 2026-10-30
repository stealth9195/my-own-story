// (실험) 사물 위치 비교 화면. 주소 끝에 ?demo 를 붙이면 열린다. 서버 없이 예시 장면만 그린다
import { useState } from "react";
import type { Page } from "./api";
import Scene from "./components/Scene";

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

export default function Demo() {
  // useState: 토글 값. 바뀌면 모든 장면을 다시 그린다
  const [placed, setPlaced] = useState(true);
  return (
    <main style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: 16 }}>
      <label style={{ fontSize: 20, fontWeight: 700, display: "flex", gap: 8, alignItems: "center" }}>
        <input type="checkbox" checked={placed} onChange={(e) => setPlaced(e.target.checked)} style={{ width: 24, height: 24 }} />
        사물 위치 정보 {placed ? "켜짐 (머리·손·하늘)" : "꺼짐 (캐릭터처럼 바닥)"}
      </label>
      {SAMPLES.map((s) => (
        <section key={s.title} style={{ width: "100%", maxWidth: 780 }}>
          <p style={{ margin: "0 0 6px" }}>{s.title}</p>
          <Scene scene={s.scene} placed={placed} />
        </section>
      ))}
    </main>
  );
}

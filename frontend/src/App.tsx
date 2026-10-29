import { useState } from "react";
import { ApiError, startStory } from "./api";
import { stopAll } from "./audio";
import { emojiOf } from "./catalog";
import Home from "./screens/Home";
import Problem from "./screens/Problem";
import StartPick from "./screens/StartPick";
import Waiting from "./screens/Waiting";
import { getAnonId, saveStory } from "./storage";
import type { SavedStory } from "./storage";
import { addSegment } from "./story";
import "./App.css";

// 라우터 없이 screen 값 하나로 화면을 바꾼다
type Screen = "home" | "pick" | "waiting" | "reading" | "shelf" | "problem";

export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [current, setCurrent] = useState<SavedStory | null>(null);
  const [waitEmoji, setWaitEmoji] = useState("📖");
  const [problem, setProblem] = useState<{ code: string; retry: () => void } | null>(null);

  function goHome() {
    stopAll();
    setScreen("home");
  }

  async function begin(cards: string[]) {
    setWaitEmoji(emojiOf(cards[0]));
    setScreen("waiting");
    try {
      const res = await startStory(getAnonId(), cards);
      const saved = addSegment(null, res, Date.now());
      await saveStory(saved);
      setCurrent(saved);
      setScreen("reading");
    } catch (e) {
      const code = e instanceof ApiError ? e.code : "unknown";
      setProblem({ code, retry: () => begin(cards) });
      setScreen("problem");
    }
  }

  switch (screen) {
    case "home":
      return <Home onNew={() => setScreen("pick")} onShelf={() => setScreen("shelf")} />;
    case "pick":
      return <StartPick onDone={begin} onBack={goHome} />;
    case "waiting":
      return <Waiting emoji={waitEmoji} />;
    case "problem":
      return <Problem code={problem!.code} onRetry={problem!.retry} onHome={goHome} />;
    case "reading":
      // 읽기 화면은 Task 5 에서 만든다. 지금은 받은 글만 보여 준다
      return (
        <main className="temp">
          {current?.segments.at(-1)?.segment.pages.map((p, i) => <p key={i}>{p.text}</p>)}
          <button className="big-button soft" onClick={goHome}>🏠 처음으로</button>
        </main>
      );
    case "shelf":
      return <main className="temp"><p>책장은 곧 만들어요</p><button className="big-button soft" onClick={goHome}>🏠 처음으로</button></main>;
  }
}

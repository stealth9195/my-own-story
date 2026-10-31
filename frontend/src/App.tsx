import { useState } from "react";
import { ApiError, sendEvent, startStory } from "./api";
import { stopAll, unlockAudio } from "./audio";
import Home from "./screens/Home";
import Problem from "./screens/Problem";
import Reading from "./screens/Reading";
import Shelf from "./screens/Shelf";
import StartPick from "./screens/StartPick";
import Waiting from "./screens/Waiting";
import { getAnonId, saveStory } from "./storage";
import type { SavedStory } from "./storage";
import { addSegment } from "./story";

// 라우터 없이 screen 값 하나로 화면을 바꾼다
type Screen = "home" | "pick" | "waiting" | "reading" | "shelf" | "problem";

export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [current, setCurrent] = useState<SavedStory | null>(null);
  const [resume, setResume] = useState(false);  // 책장에서 연 이야기인지
  const [waitCards, setWaitCards] = useState<string[]>([]);  // 기다림 화면에서 책 속으로 날아가는 고른 카드
  const [problem, setProblem] = useState<{ code: string; retry: () => void } | null>(null);

  function goHome() {
    stopAll();
    setScreen("home");
  }

  async function begin(cards: string[]) {
    setWaitCards(cards);
    setScreen("waiting");
    try {
      const res = await startStory(getAnonId(), cards);
      const saved = addSegment(null, res, Date.now());
      await saveStory(saved);
      setCurrent(saved);
      setResume(false);
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
      return <Waiting cards={waitCards} />;
    case "problem":
      return <Problem code={problem!.code} onRetry={problem!.retry} onHome={goHome} />;
    case "reading":
      // key: 이야기가 바뀌면 읽기 화면을 새로 만든다 (이전 이야기 상태가 남지 않게)
      return <Reading key={current!.story.id} saved={current!} resume={resume} onUpdate={setCurrent} onHome={goHome}
                      onNew={() => { stopAll(); setScreen("pick"); }} />;
    case "shelf":
      return (
        <Shelf
          onBack={goHome}
          onOpen={(s) => {
            unlockAudio();  // 책장에서 고른 터치로 소리 잠금 해제 (아이폰)
            sendEvent(getAnonId(), "replay", s.story.id);
            setCurrent(s);
            setResume(true);
            setScreen("reading");
          }}
        />
      );
  }
}

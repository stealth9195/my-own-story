import { useEffect } from "react";
import { speak } from "../audio";
import "./Waiting.css";

// 이야기를 만드는 동안 보여 주는 화면. 로딩 바 없이 마지막 장면의 이모지가 통통 튄다
export default function Waiting({ emoji }: { emoji: string }) {
  useEffect(() => {
    // 15초가 넘으면 한 번만 말해 준다. return 하는 함수는 화면이 사라질 때 실행된다(타이머 정리)
    const timer = setTimeout(() => speak("조금만 기다려 줘"), 15000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <main className="waiting">
      <div className="waiting-emoji" aria-hidden="true">{emoji}</div>
      <p>이야기를 만들고 있어요</p>
    </main>
  );
}

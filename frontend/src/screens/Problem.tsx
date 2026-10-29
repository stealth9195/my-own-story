import { useEffect } from "react";
import { speak } from "../audio";
import "./Problem.css";

// 서버 오류 코드 → 아이에게 들려줄 말. retry 가 있는 오류만 "다시 해볼까요?" 버튼을 보여 준다
const MESSAGES: Record<string, string> = {
  user_limit: "오늘은 이야기를 많이 들었어요. 내일 또 만나요",
  total_limit: "오늘은 이야기 친구가 쉬어요",
  regen_limit: "오늘은 이야기 친구가 쉬어요",
};
const RETRYABLE = new Set(["generation_failed", "network", "unknown"]);

type Props = { code: string; onRetry: () => void; onHome: () => void };

export default function Problem({ code, onRetry, onHome }: Props) {
  const message = MESSAGES[code] ?? "이야기가 잠깐 멈췄어요";
  useEffect(() => { speak(message); }, [message]);

  return (
    <main className="problem">
      <div className="problem-emoji" aria-hidden="true">{RETRYABLE.has(code) ? "🙈" : "🌙"}</div>
      <p>{message}</p>
      {RETRYABLE.has(code) && <button className="big-button" onClick={onRetry}>다시 해볼까요?</button>}
      <button className="big-button soft" onClick={onHome}>🏠 처음으로</button>
    </main>
  );
}

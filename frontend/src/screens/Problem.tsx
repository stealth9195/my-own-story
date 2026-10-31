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

// 폰: 가운데 정렬. PC(≥1024px): 펼친 그림책(왼쪽 쪽 큰 이모지, 오른쪽 쪽 글·버튼)
export default function Problem({ code, onRetry, onHome }: Props) {
  const message = MESSAGES[code] ?? "이야기가 잠깐 멈췄어요";
  const retryable = RETRYABLE.has(code);
  useEffect(() => { speak(message); }, [message]);

  return (
    <main className="problem">
      <div className="problem-art" aria-hidden="true"><span>{retryable ? "🙈" : "🌙"}</span></div>
      <div className="problem-body">
        <p className="problem-title display">{message}</p>
        <div className="problem-actions">
          {retryable && <button className="big-button" onClick={onRetry}>다시 해볼까요?</button>}
          <button className="big-button soft" onClick={onHome}>🏠 처음으로</button>
        </div>
      </div>
    </main>
  );
}

import { useEffect, useState } from "react";
import { getStartOptions } from "../api";
import type { StartOption, StartOptions } from "../api";
import { speak } from "../audio";
import { emojiOf } from "../catalog";
import { withJosa } from "../story";
import "./StartPick.css";

type Props = { onDone: (cards: string[]) => void; onBack: () => void };

// 처음 선택 4단계 (기획안 5장 문구 그대로)
const STEPS: { key: keyof StartOptions; question: (hero: string) => string }[] = [
  { key: "heroes", question: () => "이번 이야기의 주인공은 누구일까요?" },
  { key: "traits", question: (hero) => `${withJosa(hero, "은", "는")} 한마디로 말하면...` },
  { key: "backgrounds", question: () => "어디에서, 어떤 날 일어난 이야기일까요?" },
  { key: "objects", question: (hero) => `${withJosa(hero, "이", "가")} 가지고 있던 것은?` },
];

export default function StartPick({ onDone, onBack }: Props) {
  // useState: 화면이 기억하는 값. set 함수로 바꾸면 화면이 다시 그려진다
  const [options, setOptions] = useState<StartOptions | null>(null);
  const [step, setStep] = useState(0);
  const [picked, setPicked] = useState<StartOption[]>([]);
  const [focus, setFocus] = useState<string | null>(null);  // 한 번 누른 카드 (한 번 더 누르면 선택)
  const [failed, setFailed] = useState(false);

  // useEffect: 화면이 처음 나타날 때 한 번 실행 (후보 받아 오기)
  useEffect(() => {
    getStartOptions().then(setOptions).catch(() => setFailed(true));
  }, []);

  const hero = picked[0]?.name ?? "주인공";
  const question = STEPS[step].question(hero);

  // 질문이 바뀌면(단계 이동) 읽어 준다. [] 안의 값이 바뀔 때만 다시 실행된다
  const ready = options !== null;
  useEffect(() => {
    if (ready) speak(question);
  }, [question, ready]);

  function tap(card: StartOption) {
    if (focus !== card.id) {  // 첫 터치: 이름 읽기
      setFocus(card.id);
      speak(card.name);
      return;
    }
    const next = [...picked.slice(0, step), card];  // 두 번째 터치: 고르기
    setFocus(null);
    if (step === STEPS.length - 1) {
      onDone(next.map((c) => c.id));
    } else {
      setPicked(next);
      setStep(step + 1);
    }
  }

  function redraw() {
    // 다시 뽑기: 지금 단계 후보만 새로 받는다
    getStartOptions().then((fresh) => {
      setOptions((old) => old && { ...old, [STEPS[step].key]: fresh[STEPS[step].key] });
      setFocus(null);
    }).catch(() => setFailed(true));
  }

  function back() {
    setFocus(null);
    if (step === 0) onBack();
    else setStep(step - 1);
  }

  if (failed) {
    return (
      <main className="pick">
        <p className="pick-question">이야기 친구를 부르지 못했어요</p>
        <button className="big-button" onClick={() => location.reload()}>다시 해볼까요?</button>
      </main>
    );
  }
  if (!options) return <main className="pick"><p className="pick-question">준비하고 있어요...</p></main>;

  return (
    <main className="pick">
      <div className="pick-dots" aria-label={`${step + 1} / ${STEPS.length}`}>
        {STEPS.map((_, i) => <span key={i} className={i <= step ? "on" : ""} />)}
      </div>
      <button className="pick-question" onClick={() => speak(question)}>🔊 {question}</button>
      <div className="pick-cards">
        {options[STEPS[step].key].map((card) => (
          <button
            key={card.id}
            className={`pick-card${focus === card.id ? " focus" : ""}`}
            onClick={() => tap(card)}
          >
            <span className="pick-emoji">{card.emoji ?? emojiOf(card.id)}</span>
            <span className="pick-name">{card.name}</span>
          </button>
        ))}
      </div>
      <p className="pick-hint">{focus ? "한 번 더 누르면 골라요" : "카드를 눌러 보세요"}</p>
      <div className="pick-actions">
        <button className="big-button soft" onClick={back}>◀ 이전</button>
        <button className="big-button soft" onClick={redraw}>🔄 다시 뽑기</button>
      </div>
    </main>
  );
}

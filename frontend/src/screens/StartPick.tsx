import { useEffect, useState } from "react";
import { getStartOptions } from "../api";
import type { StartOption, StartOptions } from "../api";
import { speak } from "../audio";
import Picture from "../components/Picture";
import Settings from "../components/Settings";
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
  const [settingsOpen, setSettingsOpen] = useState(false);

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

  // 위쪽 줄: 🏠, 진행 점(끝난 단계 ✓, 지금 단계 번호), ⚙️
  const top = (
    <header className="pick-top">
      <button className="icon-button" onClick={onBack} aria-label="처음으로">🏠</button>
      <ol className="pick-dots" aria-label={`4단계 중 ${step + 1}단계`}>
        {STEPS.map((_, i) => (
          <li key={i} className={i < step ? "done" : i === step ? "now" : ""}>
            {i < step ? "✓" : i === step ? i + 1 : ""}
          </li>
        ))}
      </ol>
      <button className="icon-button" onClick={() => setSettingsOpen(true)} aria-label="설정">⚙️</button>
    </header>
  );
  const settings = settingsOpen && <Settings onClose={() => setSettingsOpen(false)} />;

  if (failed || !options) {
    return (
      <main className="pick pick-wait">
        {top}
        <div className="pick-msg">
          <span className="pick-msg-emoji" aria-hidden="true">{failed ? "🙈" : "🐻"}</span>
          <p className="pick-msg-title display">{failed ? "이야기 친구를 부르지 못했어요" : "준비하고 있어요..."}</p>
          {failed && <button className="big-button" onClick={() => location.reload()}>다시 해볼까요?</button>}
        </div>
        {settings}
      </main>
    );
  }

  const cards = options[STEPS[step].key];
  return (
    <main className="pick">
      {top}
      <div className="pick-ask">
        <button className="pick-question big-button soft" onClick={() => speak(question)}>
          <span className="pick-question-icon" aria-hidden="true">🔊</span>
          <span>{question}</span>
        </button>
        <div className="pick-deco" aria-hidden="true">
          <img src="/img/star.webp" alt="" />
          <img src="/img/moon.webp" alt="" />
        </div>
      </div>
      <div className={`pick-cards${cards.length > 4 ? " many" : ""}`}>
        {cards.map((card) => (
          <button
            key={card.id}
            className={`pick-card${focus === card.id ? " is-first" : ""}`}
            onClick={() => tap(card)}
            aria-label={focus === card.id ? `${card.name}, 한 번 더 누르면 골라요` : card.name}
          >
            {focus === card.id && <span className="pick-badge" aria-hidden="true">🔊</span>}
            {/* 성격·상황 카드는 그림 대신 이모지(card.emoji), 배경은 넓은 그림을 잘라서, 나머지는 그림 */}
            <span className={`pick-media${card.kind === "background" ? " wide" : ""}`}>
              {card.emoji ? <span className="pick-emoji">{card.emoji}</span> : <Picture id={card.id} />}
            </span>
            <span className="pick-name display">{card.name}</span>
          </button>
        ))}
      </div>
      <p className="pick-hint">{focus ? "한 번 더 누르면 골라요" : "카드를 눌러 보세요"}</p>
      <nav className="pick-actions" aria-label="이동">
        <button className="big-button soft" onClick={back}>◀ 이전</button>
        <button className="big-button secondary" onClick={redraw}>🔄 다시 뽑기</button>
      </nav>
      {settings}
    </main>
  );
}

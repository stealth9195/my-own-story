import { useEffect } from "react";
import { speak } from "../audio";
import { nameOf } from "../catalog";
import Picture from "../components/Picture";
import "./Waiting.css";

// 고른 카드가 날아오는 출발점(책 가운데 기준, 책 너비 비율)과 기울기: 왼쪽 위 → 오른쪽 위 → 왼쪽 아래 → 오른쪽 아래
const FROM = [
  { dx: -0.36, dy: -0.42, r: -8 },
  { dx: 0.36, dy: -0.42, r: 7 },
  { dx: -0.36, dy: 0.42, r: 6 },
  { dx: 0.36, dy: 0.42, r: -7 },
];

// 이야기를 만드는 동안 보여 주는 화면(서버가 잠들어 있으면 1분 넘게 걸림).
// 고른 카드 네 장이 차례로 책 속으로 날아 들어가고, 책에는 주인공 그림과 크레파스 줄이 그려진다. 숫자 진행률은 없다
export default function Waiting({ cards }: { cards: string[] }) {
  useEffect(() => {
    // 15초가 넘으면 한 번만 말해 준다. return 하는 함수는 화면이 사라질 때 실행된다(타이머 정리)
    const timer = setTimeout(() => speak("조금만 기다려 줘"), 15000);
    return () => clearTimeout(timer);
  }, []);

  const hero = cards[0];
  return (
    <main className="waiting">
      <div className="wait-stage" role="img" aria-label="고른 그림 카드가 책 속으로 날아 들어가는 그림">
        {hero && <span className="wait-hero"><Picture id={hero} /></span>}
        <div className="wait-book">
          <div className="wait-page left">{hero && <span className="wait-draw"><Picture id={hero} /></span>}</div>
          <div className="wait-page right"><i /><i /><i /><i /></div>
          {cards.slice(0, 4).map((id, i) => (
            // style 의 --이름: CSS 변수로 카드마다 출발점·순서를 넘긴다
            <span key={id} className="wait-card" style={{ "--i": i, "--dx": FROM[i].dx, "--dy": FROM[i].dy, "--r": `${FROM[i].r}deg` } as React.CSSProperties}>
              <span className="wait-card-pic"><Picture id={id} /></span>
              <span className="wait-card-name">{nameOf(id)}</span>
            </span>
          ))}
        </div>
      </div>
      <h1 className="wait-title display">이야기를 만들고 있어요</h1>
      <p className="wait-sub">고른 친구들을 책에 그리고 있어요. 조금 오래 걸릴 수도 있어요.</p>
      <div className="wait-crayons" aria-hidden="true">
        {[0, 1, 2, 3, 4, 5, 6].map((i) => (
          <svg key={i} viewBox="0 0 40 20" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round">
            <path d="M3 12 C 10 2, 18 20, 26 10 S 36 6, 38 10" />
          </svg>
        ))}
      </div>
    </main>
  );
}

import { useEffect, useState } from "react";
import { wakeServer } from "../api";
import { unlockAudio } from "../audio";
import Settings from "../components/Settings";
import "./Home.css";

// 컴포넌트: 화면 조각을 돌려주는 함수. props(부모가 넘겨준 값)로 무엇을 할지 받는다
type Props = { onNew: () => void; onShelf: () => void };

export default function Home({ onNew, onShelf }: Props) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  // useEffect(…, []): 화면이 처음 뜰 때 한 번 실행. 잠든 배포 서버를 미리 깨운다(결과는 쓰지 않음)
  useEffect(() => { wakeServer(); }, []);

  // 폰: 표지 카드 + 아래 버튼. PC(≥1024px): 펼친 그림책 — 왼쪽 쪽 그림, 오른쪽 쪽 제목·버튼 (Home.css)
  return (
    <main className="home">
      <section className="home-cover" aria-label="표지">
        <span className="home-badge" aria-hidden="true">📖</span>
        <h1 className="home-title display">나만의<br />이야기</h1>
        <svg className="home-squiggle" viewBox="0 0 140 14" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" aria-hidden="true">
          <path d="M3 8 C 14 1, 22 13, 34 7 S 54 1, 66 7 S 88 13, 100 7 S 124 2, 137 8" />
        </svg>
        <p className="home-sub">내가 고르면 이야기가 이어져요</p>
        <div className="home-art" role="img" aria-label="숲속에 곰, 보물상자, 여우가 모여 있는 그림">
          <img className="bg" src="/img/forest.webp" alt="" />
          <img className="moon" src="/img/moon.webp" alt="" />
          <img className="star s1 twinkle" src="/img/star.webp" alt="" />
          <img className="star s2 twinkle late" src="/img/star.webp" alt="" />
          <img className="home-actor bear" src="/img/bear.webp" alt="" />
          <img className="home-actor box" src="/img/treasure_box.webp" alt="" />
          <img className="home-actor fox" src="/img/fox.webp" alt="" />
        </div>
      </section>
      <div className="home-actions">
        <button
          className="big-button home-new"
          onClick={() => {
            unlockAudio();  // 첫 터치에서 소리 잠금 해제 (아이폰)
            onNew();
          }}
        >
          ✨ 새 이야기 만들기
        </button>
        <button className="big-button soft" onClick={onShelf}>📚 내 책장</button>
        <button className="home-settings" onClick={() => { unlockAudio(); setSettingsOpen(true); }}>⚙️ 설정</button>
      </div>
      {settingsOpen && <Settings onClose={() => setSettingsOpen(false)} />}
    </main>
  );
}

import { useState } from "react";
import { unlockAudio } from "../audio";
import Settings from "../components/Settings";
import "./Home.css";

// 컴포넌트: 화면 조각을 돌려주는 함수. props(부모가 넘겨준 값)로 무엇을 할지 받는다
type Props = { onNew: () => void; onShelf: () => void };

export default function Home({ onNew, onShelf }: Props) {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <main className="home">
      <div className="home-logo" aria-hidden="true">📖</div>
      <h1>나만의 이야기</h1>
      <p className="home-sub">내가 고르면 이야기가 이어져요</p>
      <button
        className="big-button"
        onClick={() => {
          unlockAudio();  // 첫 터치에서 소리 잠금 해제 (아이폰)
          onNew();
        }}
      >
        ✨ 새 이야기 만들기
      </button>
      <button className="big-button soft" onClick={onShelf}>📚 내 책장</button>
      <button className="home-settings" onClick={() => { unlockAudio(); setSettingsOpen(true); }}>⚙️ 설정</button>
      {settingsOpen && <Settings onClose={() => setSettingsOpen(false)} />}
    </main>
  );
}

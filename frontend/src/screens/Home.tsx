import { useState } from "react";
import { getGuideVoice, setGuideVoice, speak, unlockAudio } from "../audio";
import type { GuideVoice } from "../audio";
import "./Home.css";

// 컴포넌트: 화면 조각을 돌려주는 함수. props(부모가 넘겨준 값)로 무엇을 할지 받는다
type Props = { onNew: () => void; onShelf: () => void };

// (실험) 안내·질문·선택지를 읽는 목소리 비교
const GUIDE_VOICES: [GuideVoice, string][] = [["female", "여성"], ["male", "남성"], ["browser", "브라우저"]];

export default function Home({ onNew, onShelf }: Props) {
  const [voice, setVoice] = useState(getGuideVoice());

  function pickVoice(v: GuideVoice) {
    unlockAudio();
    setGuideVoice(v);
    setVoice(v);
    speak("이야기의 주인공은 누구일까요? 카드를 눌러 보세요.");
  }

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
      <div className="voice-lab">
        <span>(실험) 안내 목소리</span>
        {GUIDE_VOICES.map(([v, label]) => (
          <button key={v} className={`voice-chip${voice === v ? " on" : ""}`} onClick={() => pickVoice(v)}>{label}</button>
        ))}
      </div>
    </main>
  );
}

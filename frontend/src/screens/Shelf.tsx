import { useEffect, useState } from "react";
import { nameOf } from "../catalog";
import Picture from "../components/Picture";
import { listStories, pruneAudio } from "../storage";
import type { SavedStory } from "../storage";
import "./Shelf.css";

type Props = { onOpen: (s: SavedStory) => void; onBack: () => void; onNew: () => void };

// 책 표지 색: 빨강·파랑·초록·노랑을 차례로
const COVERS = ["#c73e08", "#1f78c8", "#1a7f4e", "#ffd23f"];

// 폰: 책 목록 한 줄씩. PC(≥1024px): 크레파스 책장에 책이 표지를 보이며 꽂혀 있다 (Shelf.css)
export default function Shelf({ onOpen, onBack, onNew }: Props) {
  const [stories, setStories] = useState<SavedStory[] | null>(null);

  useEffect(() => {
    // 오래된 이야기의 음성을 정리한 뒤 목록을 불러온다 (음성은 최근 20편만)
    pruneAudio().then(listStories).then(setStories);
  }, []);

  return (
    <main className="shelf">
      <header className="shelf-top">
        <button className="icon-button" onClick={onBack} aria-label="처음으로">🏠</button>
        <h1 className="display">📚 내 책장</h1>
        <span />
      </header>
      {stories?.length === 0 && (
        <div className="shelf-empty">
          <span className="shelf-empty-art" aria-hidden="true"><Picture id="bear" /></span>
          <p className="display">아직 책장이 비어 있어요</p>
          <button className="big-button" onClick={onNew}>✨ 새 이야기</button>
        </div>
      )}
      {!!stories?.length && (
        <ul className="shelf-books">
          {stories.map((s, i) => {
            const hero = s.story.cards[0];
            return (
              <li key={s.story.id}>
                {/* 책 한 권: 뒤표지 ← 종이 묶음 ← 앞표지 순서로 겹쳐 두께를 낸다. --c: 표지 색 */}
                <button className="book" style={{ "--c": COVERS[i % COVERS.length] } as React.CSSProperties} onClick={() => onOpen(s)}>
                  <span className="book-back" aria-hidden="true" />
                  <span className="book-pages" aria-hidden="true" />
                  <span className="book-cover" aria-hidden="true"><Picture id={hero} /></span>
                  <span className="book-meta">
                    <span className="book-title">{nameOf(hero)} 이야기</span>
                    <span className="book-date">{new Date(s.createdAt).toLocaleDateString("ko-KR")}</span>
                  </span>
                  <span className={`book-status ${s.done ? "done" : "go"}`}>{s.done ? "✔ 다 들었어요" : "▶ 이어하기"}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}

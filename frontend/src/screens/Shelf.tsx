import { useEffect, useState } from "react";
import { listStories, pruneAudio } from "../storage";
import type { SavedStory } from "../storage";
import { storyTitle } from "../story";
import "./Shelf.css";

type Props = { onOpen: (s: SavedStory) => void; onBack: () => void };

export default function Shelf({ onOpen, onBack }: Props) {
  const [stories, setStories] = useState<SavedStory[] | null>(null);

  useEffect(() => {
    // 오래된 이야기의 음성을 정리한 뒤 목록을 불러온다 (음성은 최근 20편만)
    pruneAudio().then(listStories).then(setStories);
  }, []);

  return (
    <main className="shelf">
      <header className="shelf-top">
        <button className="icon-button" onClick={onBack} aria-label="처음으로">🏠</button>
        <h1>📚 내 책장</h1>
        <span />
      </header>
      {stories?.length === 0 && <p className="shelf-empty">아직 책장이 비어 있어요</p>}
      <ul className="shelf-list">
        {stories?.map((s) => (
          <li key={s.story.id}>
            <button className="shelf-item" onClick={() => onOpen(s)}>
              <span className="shelf-title">{storyTitle(s)}</span>
              <span className="shelf-meta">
                {new Date(s.createdAt).toLocaleDateString("ko-KR")} · {s.done ? "다 들었어요" : "▶ 이어하기"}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}

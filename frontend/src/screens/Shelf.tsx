import { useEffect, useState } from "react";
import { nameOf } from "../catalog";
import Picture from "../components/Picture";
import { clearPosition } from "../position";
import { deleteStory, listStories, pruneAudio, saveStory } from "../storage";
import type { SavedStory } from "../storage";
import "./Shelf.css";

type Props = { onOpen: (s: SavedStory) => void; onBack: () => void; onNew: () => void };

// 책 표지 색: 빨강·파랑·초록·노랑을 차례로
const COVERS = ["#c73e08", "#1f78c8", "#1a7f4e", "#ffd23f"];

const titleOf = (s: SavedStory) => `${nameOf(s.story.cards[0])} 이야기`;
const dateOf = (s: SavedStory) => new Date(s.createdAt).toLocaleDateString("ko-KR");

// 폰: 책 목록 한 줄씩. PC(≥1024px): 크레파스 책장에 책이 표지를 보이며 꽂혀 있다 (Shelf.css)
// 책을 누르면 창(다시 듣기·이어하기 / 지우기)이 뜨고, 표지 왼쪽 위 하트로 좋아하는 이야기를 표시한다
export default function Shelf({ onOpen, onBack, onNew }: Props) {
  const [stories, setStories] = useState<SavedStory[] | null>(null);
  const [picked, setPicked] = useState<SavedStory | null>(null);  // 창을 띄운 이야기
  const [confirming, setConfirming] = useState(false);            // '정말 지울까요?' 단계

  useEffect(() => {
    // 오래된 이야기의 음성을 정리한 뒤 목록을 불러온다 (음성은 최근 20편만)
    pruneAudio().then(listStories).then(setStories);
  }, []);

  function toggleFavorite(s: SavedStory) {
    const updated = { ...s, favorite: !s.favorite };
    saveStory(updated);
    setStories((list) => list && list.map((x) => (x.story.id === s.story.id ? updated : x)));
  }

  async function remove(s: SavedStory) {
    await deleteStory(s.story.id);
    clearPosition(s.story.id);
    setStories((list) => list && list.filter((x) => x.story.id !== s.story.id));
    close();
  }

  function close() {
    setPicked(null);
    setConfirming(false);
  }

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
          {stories.map((s, i) => (
            <li key={s.story.id}>
              {/* 책과 하트를 한 상자에 두고 하트를 표지 왼쪽 위에 올린다 (버튼 안에 버튼은 둘 수 없어서) */}
              <div className="book-wrap" style={{ "--c": COVERS[i % COVERS.length] } as React.CSSProperties}>
                {/* 책 한 권: 뒤표지 ← 종이 묶음 ← 앞표지 순서로 겹쳐 두께를 낸다. --c: 표지 색 */}
                <button className="book" onClick={() => setPicked(s)} aria-label={`${titleOf(s)}, ${s.done ? "다 들었어요" : "이어하기"}`}>
                  <span className="book-back" aria-hidden="true" />
                  <span className="book-pages" aria-hidden="true" />
                  <span className="book-cover" aria-hidden="true"><Picture id={s.story.cards[0]} /></span>
                  <span className="book-meta">
                    <span className="book-title">{titleOf(s)}</span>
                    <span className="book-date">{dateOf(s)}</span>
                  </span>
                  <span className={`book-status ${s.done ? "done" : "go"}`}>{s.done ? "✔ 다 들었어요" : "▶ 이어하기"}</span>
                </button>
                <button className={`book-heart${s.favorite ? " on" : ""}`} aria-pressed={!!s.favorite}
                        aria-label={s.favorite ? "좋아하는 이야기 표시 끄기" : "좋아하는 이야기로 표시"} onClick={() => toggleFavorite(s)}>
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 20.5 C 5 15.5, 2.5 12, 2.5 8.6 C 2.5 5.8, 4.6 3.8, 7.2 3.8 C 9.2 3.8, 11 5, 12 6.8 C 13 5, 14.8 3.8, 16.8 3.8 C 19.4 3.8, 21.5 5.8, 21.5 8.6 C 21.5 12, 19 15.5, 12 20.5 Z" />
                  </svg>
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* 책을 누르면 뜨는 창. 바깥을 누르면 닫힘 (안쪽은 stopPropagation 으로 닫히지 않게) */}
      {picked && (
        <div className="book-dialog-backdrop" onClick={close}>
          <section className="book-dialog" role="dialog" aria-label={titleOf(picked)} onClick={(e) => e.stopPropagation()}>
            <span className="book-dialog-art" aria-hidden="true"><Picture id={picked.story.cards[0]} /></span>
            <h2 className="display">{titleOf(picked)}</h2>
            <p className="book-dialog-date">{dateOf(picked)} · {picked.done ? "다 들었어요" : "아직 만드는 중"}</p>
            {confirming ? (
              <>
                <p className="book-dialog-ask display">정말 지울까요?<br /><small>지우면 다시 볼 수 없어요</small></p>
                <div className="book-dialog-actions">
                  <button className="big-button danger" onClick={() => remove(picked)}>🗑️ 지울게요</button>
                  <button className="big-button soft" onClick={() => setConfirming(false)}>그만두기</button>
                </div>
              </>
            ) : (
              <div className="book-dialog-actions">
                {/* 다 들은 이야기는 결말 화면(처음부터·이어 듣기)으로, 만드는 중이면 멈춘 선택지부터 */}
                <button className="big-button" onClick={() => onOpen(picked)}>{picked.done ? "🔁 다시 듣기" : "▶ 이어하기"}</button>
                <button className="big-button soft" onClick={() => setConfirming(true)}>🗑️ 지우기</button>
                <button className="book-dialog-close" onClick={close}>닫기</button>
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}

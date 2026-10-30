// 다 만든 이야기를 다시 듣던 위치(구간·쪽). 새로고침하거나 책장에서 다시 열면 '이어 듣기'로 그 자리부터 듣는다.
// 작은 값이라 localStorage 에 둔다. 저장이 막힌 환경(사파리 비공개 등)에서는 조용히 넘어간다
export type Position = { view: number; page: number };

const key = (storyId: string) => `pos:${storyId}`;

export function getPosition(storyId: string): Position | null {
  try {
    const raw = localStorage.getItem(key(storyId));
    return raw ? (JSON.parse(raw) as Position) : null;
  } catch {
    return null;
  }
}

export function savePosition(storyId: string, pos: Position): void {
  try { localStorage.setItem(key(storyId), JSON.stringify(pos)); } catch { /* 무시 */ }
}

export function clearPosition(storyId: string): void {
  try { localStorage.removeItem(key(storyId)); } catch { /* 무시 */ }
}

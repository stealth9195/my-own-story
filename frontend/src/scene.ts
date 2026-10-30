// 장면 조립 계산(순수 함수). 화면(Scene.tsx)은 이 값으로 그림을 배치한다.

export type Slot = { left: number; bottom: number; scale: number };

const MAX_ACTORS = 4;

// n 명을 가로로 고르게 놓는다(left 는 % 위치, 그림 가운데 기준). 많을수록 조금 작게
export function actorSlots(n: number): Slot[] {
  const count = Math.min(Math.max(n, 0), MAX_ACTORS);
  const scale = count <= 2 ? 1 : 0.8;
  return Array.from({ length: count }, (_, i) => ({
    left: count === 1 ? 50 : 15 + (70 * i) / (count - 1),
    bottom: 6,
    scale,
  }));
}

// 상태 효과: 캐릭터 머리 위에 작게 띄우는 표시 (기획안 7장)
const STATE_MARKS: Record<string, string> = {
  talking: "💬",
  sleeping: "💤",
  surprised: "❗",
  happy: "💕",
  thinking: "💭",
  scared: "💦",
  walking: "👣",
};

export function stateMark(state: string): string | null {
  return STATE_MARKS[state] ?? null;
}

// 시간대: 배경 그림에 CSS 필터를 씌워 노을·밤을 만든다 (그림을 따로 만들지 않음)
const TIME_FILTERS: Record<string, string> = {
  sunset: "sepia(0.3) saturate(1.3)",
  night: "brightness(0.6) saturate(0.8)",
};

export function timeFilter(time: string): string {
  return TIME_FILTERS[time] ?? "none";
}

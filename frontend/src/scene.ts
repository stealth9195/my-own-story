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

export type Facing = "left" | "right" | "front";
export type Actor = { id: string; state: string | null; object: boolean; flip: boolean; looks: Facing };

const asFacing = (f: string): Facing => (f === "left" || f === "right" ? f : "front");

// 장면에 세울 순서(왼쪽→오른쪽)와 좌우 반전을 정한다.
// 1) 오른쪽을 보는 캐릭터는 왼쪽에, 정면은 가운데, 왼쪽을 보는 캐릭터는 오른쪽에 → 서로 마주 봄
// 2) 그래도 가운데를 등지는 캐릭터(같은 방향이 둘 이상)는 그릴 때만 뒤집는다. 정면·가운데 자리는 뒤집지 않음
// 3) 사물은 캐릭터 뒤(오른쪽)에, 모두 합쳐 최대 4개
export function arrangeActors(characters: { id: string; state: string; facing: string }[], objects: string[]): Actor[] {
  const rank: Record<Facing, number> = { right: 0, front: 1, left: 2 };
  const chars = characters
    .map((c) => ({ ...c, facing: asFacing(c.facing) }))
    .sort((a, b) => rank[a.facing] - rank[b.facing]);  // 같은 방향끼리는 원래 순서 유지
  const all = [
    ...chars.map((c) => ({ id: c.id, state: c.state, object: false, facing: c.facing })),
    ...objects.map((id) => ({ id, state: null, object: true, facing: "front" as Facing })),
  ].slice(0, MAX_ACTORS);
  const slots = actorSlots(all.length);
  return all.map((a, i) => {
    const want: Facing = slots[i].left < 50 ? "right" : slots[i].left > 50 ? "left" : "front";
    const flip = a.facing !== "front" && want !== "front" && a.facing !== want;
    const looks: Facing = flip ? want : a.facing;
    return { id: a.id, state: a.state, object: a.object, flip, looks };
  });
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

// 시간대: 배경 그림의 밝기·채도를 조절한다. 색(밤 남색·노을 주황)은 Scene.css 의 색 덮기가 맡는다
const TIME_FILTERS: Record<string, string> = {
  sunset: "saturate(1.2)",
  night: "brightness(0.85) saturate(0.85)",
};

export function timeFilter(time: string): string {
  return TIME_FILTERS[time] ?? "none";
}

// ── 사물 위치 ──
// catalog 의 place 로 사물을 둔다. head(왕관)·hand(요술봉)는 캐릭터에게 붙이고(캐릭터마다 하나씩),
// sky(달·별)는 장면 위쪽, 나머지와 붙일 캐릭터가 없는 것은 바닥(캐릭터 옆)에 세운다
export type Worn = { id: string; on: string; place: "head" | "hand" };

export function placeObjects(characterIds: string[], objects: string[], placeOf: (id: string) => string | undefined):
  { worn: Worn[]; sky: string[]; ground: string[] } {
  const worn: Worn[] = [];
  const sky: string[] = [];
  const ground: string[] = [];
  for (const id of objects) {
    const place = placeOf(id);
    if (place === "sky") { sky.push(id); continue; }
    if (place === "head" || place === "hand") {
      const on = characterIds.find((c) => !worn.some((w) => w.on === c && w.place === place));
      if (on) { worn.push({ id, on, place }); continue; }
    }
    ground.push(id);
  }
  return { worn, sky, ground };
}

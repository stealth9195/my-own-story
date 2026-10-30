// 그림·소리 목록. 백엔드와 같은 파일(shared/catalog.json)을 쓴다.
// 그림 에셋이 나오기 전까지 카드·장면은 이모지로 보여 준다.
import catalog from "../../shared/catalog.json";

type Asset = { id: string; name: string; emoji?: string; facing?: string };

const KINDS = ["characters", "objects", "backgrounds", "traits", "situations"] as const;
const byId = new Map<string, Asset>(
  KINDS.flatMap((kind) => (catalog[kind] as Asset[]).map((a) => [a.id, a] as const)),
);

export function emojiOf(id: string): string {
  return byId.get(id)?.emoji ?? "❓";
}

export function nameOf(id: string): string {
  return byId.get(id)?.name ?? id;
}

// 그림 속 캐릭터가 보는 방향(left·right·front). 안 적었으면 ""
export function facingOf(id: string): string {
  return byId.get(id)?.facing ?? "";
}

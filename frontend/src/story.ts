// 이야기 진행 계산 (화면과 상관없는 순수 함수라 테스트하기 쉽다)
import type { Segment, SegmentResponse, SignedSegment, StoryKey } from "./api";
import { emojiOf, nameOf } from "./catalog";
import type { SavedStory } from "./storage";

// 서버 응답을 저장할 이야기에 붙인다. React 상태는 바꾸지 않고 새 값을 만들어야 화면이 다시 그려진다
export function addSegment(saved: SavedStory | null, res: SegmentResponse, now: number): SavedStory {
  if (!saved) return { story: res.story, segments: [res.segment], chosen: [], createdAt: now, done: res.done };
  return { ...saved, segments: [...saved.segments, res.segment], done: res.done };
}

export function choose(saved: SavedStory, choiceId: string): SavedStory {
  return { ...saved, chosen: [...saved.chosen, choiceId] };
}

export function nextArgs(saved: SavedStory): { story: StoryKey; history: SignedSegment[]; chosen: string[] } {
  return { story: saved.story, history: saved.segments, chosen: saved.chosen };
}

// 구간 음성 하나에 페이지 여러 장이 들어 있으므로, 글자 수 비율로 페이지가 시작하는 시각(초)을 정한다
export function pageStartTimes(pages: string[], duration: number): number[] {
  const total = pages.reduce((n, p) => n + p.length, 0) || 1;
  let acc = 0;
  return pages.map((p) => {
    const start = (acc / total) * duration;
    acc += p.length;
    return start;
  });
}

export function pageAt(time: number, starts: number[]): number {
  let page = 0;
  starts.forEach((s, i) => { if (time >= s) page = i; });
  return page;
}

export function storyTitle(saved: SavedStory): string {
  const hero = saved.story.cards[0];
  return `${emojiOf(hero)} ${nameOf(hero)} 이야기`;
}

export function segmentText(seg: Segment): string {
  return seg.pages.map((p) => p.text).join("\n");
}

// 받침이 있으면 앞 조사(은/이), 없으면 뒤 조사(는/가). 예: 곰은, 오리는
export function withJosa(word: string, withFinal: string, withoutFinal: string): string {
  const code = word.charCodeAt(word.length - 1) - 0xac00;
  const hasFinal = code >= 0 && code <= 11171 && code % 28 !== 0;
  return word + (hasFinal ? withFinal : withoutFinal);
}

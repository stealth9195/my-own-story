// 백엔드 서비스 API 호출. 타입 이름은 backend/app/api/schemas.py 와 같게 맞춘다.

export type Voice = {
  // browser: 서버 음성 한도가 부족해 처음부터 브라우저 음성으로 읽는 이야기
  provider: "gemini" | "typecast" | "browser";
  model?: string | null;
  voice?: string | null;
};

export type StoryKey = {
  id: string;
  cards: string[];
  choice_count: number;
  voice: Voice;
};

export type Page = {
  text: string;
  scene: {
    background: string;
    time: string;
    characters: { id: string; state: string }[];
    objects: string[];
  };
  mood: string;
  sfx: string | null;
};

export type Choice = { kind: "item" | "phrase"; id: string; label: string };

export type Segment = { type: "intro" | "middle" | "ending"; pages: Page[]; choices: Choice[] };

// 서버가 만든 구간 + 서명. 다음 요청에 그대로 돌려보낸다 (서버는 저장하지 않음)
export type SignedSegment = { segment: Segment; sig: string };

export type SegmentResponse = { story: StoryKey; index: number; segment: SignedSegment; done: boolean };

export type StartOption = { id: string; name: string; kind: string; emoji: string | null };

export type StartOptions = {
  heroes: StartOption[];
  traits: StartOption[];
  backgrounds: StartOption[];
  objects: StartOption[];
};

export type EventType = "card_select" | "choice_time" | "drop_off" | "complete" | "replay" | "mute" | "error";

export class ApiError extends Error {
  status: number;
  // 서버 오류 코드(user_limit, generation_failed 등). 서버에 닿지 못하면 "network"
  code: string;

  constructor(status: number, code: string) {
    super(`${status} ${code}`);
    this.status = status;
    this.code = code;
  }
}

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function request(path: string, body?: unknown): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(BASE + path, body === undefined ? undefined : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network");
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, data?.detail?.code ?? "unknown");
  }
  return res;
}

export async function getStartOptions(): Promise<StartOptions> {
  return (await request("/api/start-options")).json();
}

export async function startStory(anonId: string, cards: string[], choiceCount = 4): Promise<SegmentResponse> {
  return (await request("/api/stories", { anon_id: anonId, cards, choice_count: choiceCount })).json();
}

export async function nextSegment(anonId: string, story: StoryKey, history: SignedSegment[],
                                  chosen: string[]): Promise<SegmentResponse> {
  return (await request("/api/stories/next", { anon_id: anonId, story, history, chosen })).json();
}

export async function fetchSegmentAudio(story: StoryKey, index: number, segment: SignedSegment): Promise<Blob> {
  return (await request("/api/tts", { story, index, segment })).blob();
}

// 사용 기록. 실패해도 무시한다 (기록 때문에 이야기가 멈추면 안 됨)
export function sendEvent(anonId: string, type: EventType, storyId?: string, payload: object = {}): void {
  request("/api/events", { anon_id: anonId, type, story_id: storyId ?? null, payload }).catch(() => {});
}

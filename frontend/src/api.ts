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

// 응답을 기다리는 최대 시간. 휴대폰 네트워크가 끊겨 응답이 안 오면 아이가 대기 화면에 갇히므로
// 시간이 지나면 "network" 오류로 바꿔 "다시 해볼까요?"를 보여 준다.
// 서버는 구간 생성에 최대 약 2분(모델 대기 60초 + 다시 생성), 음성은 10~20초(재시도 포함하면 더) 걸릴 수 있다
export const STORY_TIMEOUT_MS = 120_000;
export const AUDIO_TIMEOUT_MS = 90_000;
const DEFAULT_TIMEOUT_MS = 20_000;

async function request(path: string, body?: unknown, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      signal: abort.signal,
      ...(body === undefined ? {} : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    });
  } catch {
    throw new ApiError(0, "network");
  } finally {
    clearTimeout(timer);
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
  return (await request("/api/stories", { anon_id: anonId, cards, choice_count: choiceCount }, STORY_TIMEOUT_MS)).json();
}

export async function nextSegment(anonId: string, story: StoryKey, history: SignedSegment[],
                                  chosen: string[]): Promise<SegmentResponse> {
  return (await request("/api/stories/next", { anon_id: anonId, story, history, chosen }, STORY_TIMEOUT_MS)).json();
}

// (실험) 문장 사이 쉼(초). 설정 창에서 정하면 TTS 연출 지시의 'short pause' 대신 그 초로 보낸다
export function getTtsPause(): number | null {
  try {
    const v = localStorage.getItem("ttsPause");
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}

export function setTtsPause(v: number | null): void {
  try {
    if (v === null) localStorage.removeItem("ttsPause");
    else localStorage.setItem("ttsPause", String(v));
  } catch { /* 무시 */ }
}

export async function fetchSegmentAudio(story: StoryKey, index: number, segment: SignedSegment): Promise<Blob> {
  return (await request("/api/tts", { story, index, segment, pause: getTtsPause() }, AUDIO_TIMEOUT_MS)).blob();
}

// 사용 기록. 실패해도 무시한다 (기록 때문에 이야기가 멈추면 안 됨)
export function sendEvent(anonId: string, type: EventType, storyId?: string, payload: object = {}): void {
  request("/api/events", { anon_id: anonId, type, story_id: storyId ?? null, payload }).catch(() => {});
}

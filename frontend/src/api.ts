// 백엔드 서비스 API 호출. 타입 이름은 backend/app/api/schemas.py 와 같게 맞춘다.

export type Voice = {
  // browser: 서버 음성 한도가 부족해 처음부터 브라우저 음성으로 읽는 이야기
  provider: "gemini" | "typecast" | "elevenlabs" | "browser";
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

export type EventType = "card_select" | "choice_time" | "drop_off" | "complete" | "replay" | "mute" | "error"
  | "voice_failed";  // 이야기 음성을 못 받았거나 재생이 막힘 (payload: index, reason)

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

// 배포 서버(Render 무료)는 15분 쉬면 잠들고, 깨는 데 약 1분 걸린다.
// 홈 화면이 뜨면 미리 깨우고(wakeServer), 처음 선택 후보도 그만큼 기다린다
export const WAKE_TIMEOUT_MS = 70_000;

export async function getStartOptions(): Promise<StartOptions> {
  return (await request("/api/start-options", undefined, WAKE_TIMEOUT_MS)).json();
}

export function wakeServer(): void {
  request("/api/start-options", undefined, WAKE_TIMEOUT_MS).catch(() => {});
}

// 이야기 목소리 (설정, Gemini 목소리 이름). "" 이면 무작위. 새 이야기부터 적용
export const STORY_VOICES: [string, string][] = [["", "무작위"], ["Kore", "또렷한"], ["Aoede", "산뜻한"], ["Leda", "앳된"]];

// 시연용 목소리(ElevenLabs): 서버에 설정돼 있을 때만 [번호, 이름] 목록이 온다. 못 받으면 빈 목록
export async function getDemoVoices(): Promise<[string, string][]> {
  try {
    const list: { id: string; name: string }[] = await (await request("/api/voices")).json();
    return list.map((v) => [v.id, v.name]);
  } catch {
    return [];
  }
}

export function getStoryVoice(): string {
  try { return localStorage.getItem("storyVoice") ?? ""; } catch { return ""; }
}

export function setStoryVoice(v: string): void {
  try { localStorage.setItem("storyVoice", v); } catch { /* 이번 실행에만 적용 */ }
}

export async function startStory(anonId: string, cards: string[], choiceCount = 4): Promise<SegmentResponse> {
  const voice = getStoryVoice();
  return (await request("/api/stories", { anon_id: anonId, cards, choice_count: choiceCount, voice: voice || null }, STORY_TIMEOUT_MS)).json();
}

export async function nextSegment(anonId: string, story: StoryKey, history: SignedSegment[],
                                  chosen: string[]): Promise<SegmentResponse> {
  return (await request("/api/stories/next", { anon_id: anonId, story, history, chosen }, STORY_TIMEOUT_MS)).json();
}

export async function fetchSegmentAudio(story: StoryKey, index: number, segment: SignedSegment): Promise<Blob> {
  return (await request("/api/tts", { story, index, segment }, AUDIO_TIMEOUT_MS)).blob();
}

// 사용 기록. 실패해도 무시한다 (기록 때문에 이야기가 멈추면 안 됨)
export function sendEvent(anonId: string, type: EventType, storyId?: string, payload: object = {}): void {
  request("/api/events", { anon_id: anonId, type, story_id: storyId ?? null, payload }).catch(() => {});
}

import { bgmPlayer, sfxPlayer } from "./sound";

// 소리 재생. 아이폰(Safari)은 사용자가 화면을 터치하기 전에는 소리를 막는다.
// 그래서 첫 터치("새 이야기 만들기")에서 오디오 요소 하나를 '잠금 해제'해 두고, 이후 이야기 음성은 모두 그 요소로 재생한다.

export const player: HTMLAudioElement | null = typeof Audio === "undefined" ? null : new Audio();
// 안내·질문·선택지를 읽는 요소 (이야기 음성과 따로)
const guidePlayer: HTMLAudioElement | null = typeof Audio === "undefined" ? null : new Audio();

// 0.1초짜리 무음 WAV (잠금 해제용으로 한 번 재생)
function silentWav(): string {
  const samples = 2400;
  const buf = new ArrayBuffer(44 + samples * 2);
  const v = new DataView(buf);
  const text = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  text(0, "RIFF"); v.setUint32(4, 36 + samples * 2, true); text(8, "WAVE");
  text(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, 24000, true); v.setUint32(28, 48000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  text(36, "data"); v.setUint32(40, samples * 2, true);
  return URL.createObjectURL(new Blob([buf], { type: "audio/wav" }));
}

// 목소리 크기 (이야기 음성·안내 목소리, 0~1). 기기에 저장
let voiceVolume = (() => {
  try {
    const v = localStorage.getItem("voiceVolume");
    return v === null ? 1 : Math.min(Math.max(Number(v), 0), 1);
  } catch {
    return 1;
  }
})();
if (player) player.volume = voiceVolume;
if (guidePlayer) guidePlayer.volume = voiceVolume;

export function getVoiceVolume(): number {
  return voiceVolume;
}

export function setVoiceVolume(v: number): void {
  voiceVolume = v;
  try { localStorage.setItem("voiceVolume", String(v)); } catch { /* 이번 실행에만 적용 */ }
  if (player) player.volume = v;
  if (guidePlayer) guidePlayer.volume = v;
}

let unlocked = false;

export function unlockAudio(): void {
  if (unlocked) return;
  unlocked = true;
  const silent = silentWav();
  if (player) {
    player.src = silent;
    player.play().catch(() => {});
  }
  // 배경 음악·효과음 요소도 같은 터치에서 잠금 해제 (음악은 반복 재생이라 바로 멈춘다)
  for (const el of [bgmPlayer, sfxPlayer, guidePlayer]) {
    if (!el) continue;
    el.src = silent;
    el.play().then(() => el.pause()).catch(() => {});
  }
  // 브라우저 음성(speechSynthesis)도 첫 터치에서 한 번 불러 둔다
  if (typeof speechSynthesis !== "undefined") speechSynthesis.speak(new SpeechSynthesisUtterance(""));
}

// 안내 목소리: Azure 여성·남성(서버 /api/speak) 또는 브라우저 음성. 기기에 저장
export type GuideVoice = "browser" | "female" | "male";
let guideVoice: GuideVoice = readGuideVoice();

function readGuideVoice(): GuideVoice {
  try {
    const v = localStorage.getItem("guideVoice");
    return v === "browser" || v === "male" ? v : "female";
  } catch {
    return "female";
  }
}

export function getGuideVoice(): GuideVoice {
  return guideVoice;
}

export function setGuideVoice(v: GuideVoice): void {
  guideVoice = v;
  try { localStorage.setItem("guideVoice", v); } catch { /* 이번 실행에만 적용 */ }
}

// 같은 글·목소리는 한 번만 받아 둔다 (질문 문장은 매번 같아서 서버 글자 한도를 아낀다)
const spoken = new Map<string, Promise<string>>();
let speakToken = 0;

function fetchSpeech(text: string, voice: "female" | "male"): Promise<string> {
  const key = `${voice}:${text}`;
  let req = spoken.get(key);
  if (!req) {
    req = fetch(`${import.meta.env.VITE_API_BASE ?? ""}/api/speak`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, voice }),
    }).then(async (res) => {
      if (!res.ok) throw new Error(`speak ${res.status}`);
      return URL.createObjectURL(await res.blob());
    });
    req.catch(() => spoken.delete(key));  // 실패는 기억하지 않음 (다음에 다시 시도)
    spoken.set(key, req);
  }
  return req;
}

// 질문·선택지·안내 읽기. 끝나면 resolve. Azure 가 안 되면(키 없음·한도·오류) 브라우저 음성으로
export function speak(text: string, rate = 0.95): Promise<void> {
  if (!text) return Promise.resolve();
  const t = ++speakToken;
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
  guidePlayer?.pause();
  const voice = guideVoice;
  if (voice === "browser" || !guidePlayer) return speakBrowser(text, rate);
  return fetchSpeech(text, voice).then((url) => new Promise<void>((resolve) => {
    if (t !== speakToken) return resolve();  // 받는 동안 다른 말을 시작했으면 읽지 않음
    guidePlayer.src = url;
    guidePlayer.onended = () => resolve();
    guidePlayer.onerror = () => resolve();
    guidePlayer.play().catch(() => resolve());
  })).catch(() => (t === speakToken ? speakBrowser(text, rate) : undefined));
}

// 이야기 목소리 미리 듣기 (public/voice/{이름}.mp3, 실험 중 만든 샘플). 서버 음성 한도를 쓰지 않는다
export function playVoicePreview(name: string): void {
  speakToken++;
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
  if (!guidePlayer) return;
  guidePlayer.src = `/voice/${name}.mp3`;
  guidePlayer.play().catch(() => {});
}

export function stopVoicePreview(): void {
  guidePlayer?.pause();
}

// 브라우저 음성 (무료, 기계음). 지원하지 않으면 바로 resolve
function speakBrowser(text: string, rate: number): Promise<void> {
  if (typeof speechSynthesis === "undefined") return Promise.resolve();
  speechSynthesis.cancel();
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "ko-KR";
    u.rate = rate;
    u.volume = voiceVolume;
    const done = () => { clearTimeout(timer); resolve(); };
    // 일부 브라우저는 끝 이벤트를 안 보내서, 글 길이로 넉넉히 잡은 시간이 지나면 끝난 것으로 본다
    const timer = setTimeout(done, 2000 + text.length * 250);
    u.onend = done;
    u.onerror = done;
    speechSynthesis.speak(u);
  });
}

// 재생 순번. 화면을 떠나거나 다음 구간으로 가면 새 번호를 받는다.
// 음성은 받는 데 10초 넘게 걸릴 수 있어서, 도착했을 때 번호가 바뀌었으면 재생하지 않는다
let token = 0;

export function playToken(): number {
  token += 1;
  return token;
}

export function isCurrent(t: number): boolean {
  return t === token;
}

export function stopAll(): void {
  playToken();
  speakToken++;
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
  player?.pause();
  guidePlayer?.pause();
}

// 재생 배속 (부모용 '더 느리게·더 빠르게'). 기본 속도는 TTS 연출 지시로 맞추고, 이건 미세 조정용. 기기에 저장
export const RATES = [0.8, 0.9, 1, 1.1, 1.2, 1.3];

export function getRate(): number {
  try {
    const r = Number(localStorage.getItem("rate"));
    return RATES.includes(r) ? r : 1;
  } catch {
    return 1;
  }
}

export function stepRate(rate: number, dir: 1 | -1): number {
  const i = RATES.indexOf(rate);
  return RATES[Math.min(Math.max((i < 0 ? RATES.indexOf(1) : i) + dir, 0), RATES.length - 1)];
}

export function setRate(r: number): void {
  try { localStorage.setItem("rate", String(r)); } catch { /* 저장 못 해도 이번 재생에는 적용 */ }
  if (player) player.playbackRate = r;
}

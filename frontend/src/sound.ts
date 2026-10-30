// 배경 음악·효과음. 이야기 음성(audio.ts 의 player)과 따로 재생한다.
// 파일: 음악 public/bgm/{id}.mp3, 효과음 public/sound/{id}.mp3. 없거나 재생 실패는 모두 조용히 넘어간다.
// 음소거는 음악·효과음만 끈다. 이야기 음성은 구연동화의 핵심이라 계속 들린다.
import catalog from "../../shared/catalog.json";

export type Bgm = { id: string; name: string; mood: string };

export const BGM: Bgm[] = catalog.bgm;

const VOLUME = 0.4;       // 평소 음악 크기
const DUCK_VOLUME = 0.15; // 이야기 음성이 나오는 동안
const SFX_VOLUME = 0.7;

const makeAudio = () => (typeof Audio === "undefined" ? null : new Audio());
export const bgmPlayer = makeAudio();
export const sfxPlayer = makeAudio();
if (bgmPlayer) bgmPlayer.loop = true;

// play() 실패(파일 없음·자동 재생 막힘)는 무시. 일부 환경은 Promise 를 돌려주지 않아 try 로도 감싼다
function safePlay(el: HTMLAudioElement): void {
  try { el.play()?.catch(() => {}); } catch { /* 무시 */ }
}

// 분위기에 맞는 곡 고르기. 결말은 ending → warm → calm, 그 밖에는 같은 분위기 → calm.
// 같은 분위기 곡이 여럿이면 rng 로 하나 (이야기마다 같은 rng 를 쓰면 이야기 안에서는 같은 곡)
export function pickBgm(bgm: Bgm[], mood: string, ending: boolean, rng: () => number): string | null {
  const order = ending ? ["ending", "warm", "calm"] : [mood, "calm"];
  for (const m of order) {
    const songs = bgm.filter((b) => b.mood === m);
    if (songs.length) return songs[Math.min(Math.floor(rng() * songs.length), songs.length - 1)].id;
  }
  return null;
}

// 이야기 id 로 정해지는 0~1 값 (같은 이야기는 다시 열어도 같은 곡)
export function storyRng(storyId: string): () => number {
  let h = 0;
  for (const c of storyId) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return () => h / 2 ** 32;
}

// 음악·효과음 크기 (설정 창, 0~1). 기기에 저장
let musicVolume = readNumber("musicVolume", 1);

function readNumber(key: string, fallback: number): number {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : Math.min(Math.max(Number(v), 0), 1);
  } catch {
    return fallback;
  }
}

export function getMusicVolume(): number {
  return musicVolume;
}

export function setMusicVolume(v: number): void {
  musicVolume = v;
  try { localStorage.setItem("musicVolume", String(v)); } catch { /* 이번 실행에만 적용 */ }
  if (bgmPlayer) bgmPlayer.volume = (ducked ? DUCK_VOLUME : VOLUME) * musicVolume;
}

let muted = readMuted();
let currentBgm: string | null = null;
let ducked = false;

function readMuted(): boolean {
  try { return localStorage.getItem("muted") === "1"; } catch { return false; }
}

export function isMuted(): boolean {
  return muted;
}

export function setMuted(m: boolean): void {
  muted = m;
  try { localStorage.setItem("muted", m ? "1" : "0"); } catch { /* 저장 못 해도 이번 실행에는 적용 */ }
  if (m) {
    bgmPlayer?.pause();
    sfxPlayer?.pause();
  } else if (currentBgm) {
    if (bgmPlayer) safePlay(bgmPlayer);
  }
}

export function playBgm(id: string | null): void {
  if (!bgmPlayer) return;
  if (id === currentBgm) return;  // 같은 곡이면 끊지 않고 이어서
  currentBgm = id;
  if (!id) { bgmPlayer.pause(); return; }
  bgmPlayer.src = `/bgm/${id}.mp3`;
  bgmPlayer.volume = (ducked ? DUCK_VOLUME : VOLUME) * musicVolume;
  if (!muted) safePlay(bgmPlayer);
}

export function duckBgm(on: boolean): void {
  ducked = on;
  if (bgmPlayer) bgmPlayer.volume = (on ? DUCK_VOLUME : VOLUME) * musicVolume;
}

export function playSfx(id: string | null): void {
  if (!sfxPlayer || !id || muted) return;
  sfxPlayer.src = `/sound/${id}.mp3`;
  sfxPlayer.volume = SFX_VOLUME * musicVolume;
  safePlay(sfxPlayer);
}

export function stopSound(): void {
  currentBgm = null;
  bgmPlayer?.pause();
  sfxPlayer?.pause();
}

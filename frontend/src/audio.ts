// 소리 재생. 아이폰(Safari)은 사용자가 화면을 터치하기 전에는 소리를 막는다.
// 그래서 첫 터치("새 이야기 만들기")에서 오디오 요소 하나를 '잠금 해제'해 두고, 이후 이야기 음성은 모두 그 요소로 재생한다.

export const player: HTMLAudioElement | null = typeof Audio === "undefined" ? null : new Audio();

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

let unlocked = false;

export function unlockAudio(): void {
  if (unlocked) return;
  unlocked = true;
  if (player) {
    player.src = silentWav();
    player.play().catch(() => {});
  }
  // 브라우저 음성(speechSynthesis)도 첫 터치에서 한 번 불러 둔다
  if (typeof speechSynthesis !== "undefined") speechSynthesis.speak(new SpeechSynthesisUtterance(""));
}

// 질문·선택지 읽기용 브라우저 음성 (무료). 끝나면 resolve. 지원하지 않으면 바로 resolve
export function speak(text: string, rate = 0.95): Promise<void> {
  if (typeof speechSynthesis === "undefined" || !text) return Promise.resolve();
  speechSynthesis.cancel();
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "ko-KR";
    u.rate = rate;
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
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
  player?.pause();
}

// 읽기 속도 (TTS 지시문 대신 재생 속도로 조절, 기기에 저장)
export const SPEEDS = { slow: 0.85, normal: 1.0 } as const;
export type Speed = keyof typeof SPEEDS;

export function getSpeed(): Speed {
  try {
    return localStorage.getItem("speed") === "normal" ? "normal" : "slow";
  } catch {
    return "slow";
  }
}

export function setSpeed(s: Speed): void {
  try { localStorage.setItem("speed", s); } catch { /* 저장 못 해도 이번 재생에는 적용 */ }
  if (player) player.playbackRate = SPEEDS[s];
}

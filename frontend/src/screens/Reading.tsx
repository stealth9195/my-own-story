import { useEffect, useRef, useState } from "react";
import { ApiError, fetchSegmentAudio, nextSegment, sendEvent } from "../api";
import type { Choice } from "../api";
import { getRate, getVoiceVolume, isCurrent, player, playToken, speak, stopAll, watchEnd } from "../audio";
import { emojiOf } from "../catalog";
import Settings from "../components/Settings";
import { getAnonId, getAudio, saveAudio, saveStory } from "../storage";
import type { SavedStory } from "../storage";
import { addSegment, choose, nextArgs, pageAt, pageStartTimes } from "../story";
import Picture from "../components/Picture";
import { clearPosition, getPosition, savePosition } from "../position";
import { BGM, duckBgm, isMuted, pickBgm, playBgm, playSfx, setMuted, stopSound, storyRng } from "../sound";
import Scene from "../components/Scene";
import Problem from "./Problem";
import "./Reading.css";

// resume: 책장에서 연 이야기. 다 들은 이야기는 결말 화면부터, 아니면 마지막 선택지부터 시작
type Props = { saved: SavedStory; resume?: boolean; onUpdate: (s: SavedStory) => void; onHome: () => void;
               onNew: () => void };

// loading: 음성 받는 중(다음 장 잠금) / playing: 음성 재생 중 / manual: 음성 없이 버튼으로 넘김
// choices: 선택지 / waiting: 다음 구간 만드는 중 / problem: 오류 / end: 결말까지 들음
type Phase = "loading" | "playing" | "manual" | "choices" | "waiting" | "problem" | "end";

// 같은 구간 음성 요청을 하나로 묶는다. 개발 모드(StrictMode)는 화면 준비를 두 번 실행하는데,
// 그때마다 서버 음성을 부르면 구간당 2번 한도와 Gemini 하루 한도를 헛되이 쓴다
const audioRequests = new Map<string, Promise<Blob>>();

function loadAudio(saved: SavedStory, index: number): Promise<Blob> {
  const key = `${saved.story.id}:${index}`;
  let req = audioRequests.get(key);
  if (!req) {
    req = fetchSegmentAudio(saved.story, index, saved.segments[index])
      .then(async (mp3) => { await saveAudio(saved.story.id, index, mp3); return mp3; })
      .finally(() => audioRequests.delete(key));
    audioRequests.set(key, req);
  }
  return req;
}

export default function Reading({ saved, resume = false, onUpdate, onHome, onNew }: Props) {
  const last = saved.segments.length - 1;
  const [view, setView] = useState(last);       // 보여 주는 구간 (다시 듣기 때는 0부터)
  const [page, setPage] = useState(0);
  const [phase, setPhase] = useState<Phase>("loading");
  const [focus, setFocus] = useState<string | null>(null);
  const [problem, setProblem] = useState("unknown");
  const [muted, setMutedState] = useState(isMuted());
  const [paused, setPaused] = useState(false);       // 부모가 잠깐 멈춤
  const [settingsOpen, setSettingsOpen] = useState(false);
  const textEnd = useRef<HTMLParagraphElement | null>(null);  // 마지막으로 읽는 쪽 (자동 스크롤)
  // useRef: 화면을 다시 그려도 유지되지만, 바뀌어도 다시 그리지는 않는 값 (마지막 선택 요청 기억)
  const pending = useRef<SavedStory | null>(null);
  const resuming = useRef(resume);  // 이어하기로 연 구간에서만 true
  const requesting = useRef(false);
  // 다시 듣기 중인지. 화면에 보일 값이 아니라서 ref (state 로 두면 바뀔 때 구간 준비가 다시 실행돼 결말을 또 재생했음)
  const replaying = useRef(false);
  // '이어 듣기'로 시작할 쪽. 음성 길이를 알게 되면 그 쪽 위치로 옮기고 지운다
  const startAt = useRef<number | null>(null);
  // 같은 구간에서 다시 시작할 때(이어 듣기 위치가 지금 구간) 준비 단계를 다시 돌리기 위한 번호
  const [restart, setRestart] = useState(0);

  const signed = saved.segments[view];
  const seg = signed.segment;
  const isEnding = seg.type === "ending";
  // 구간이 바뀐 직후 한 번은 이전 구간의 페이지 번호로 그려진다(번호는 다음 준비 단계에서 0으로 바뀜).
  // 새 구간이 더 짧으면 없는 페이지를 읽어 화면이 멈췄으므로, 그 구간의 마지막 쪽을 넘지 않게 한다
  const shown = seg.pages[Math.min(page, seg.pages.length - 1)];

  // 구간이 바뀔 때마다: 글을 먼저 보여 주고, 음성을 받아 오면 자동 재생
  useEffect(() => {
    const t = playToken();
    setPage(startAt.current ?? 0);  // 이어 듣기·이전/다음이면 그 쪽을 바로 보여 준다 (음성 위치는 길이를 안 뒤 맞춤)
    setFocus(null);
    setPaused(false);
    setPhase("loading");

    const finish = () => { if (isCurrent(t)) afterSegment(); };
    let stopWatch = () => {};

    async function run() {
      // resuming 은 다른 구간으로 넘어갈 때 끈다 (개발 모드는 이 준비를 두 번 실행하므로 여기서 끄면 안 됨)
      if (resuming.current) {
        if (saved.done) {
          setPage(seg.pages.length - 1);
          setPhase("end");
        } else if (saved.chosen.length === saved.segments.length) {
          request(saved);  // 고른 뒤 다음 구간을 받기 전에 멈췄던 이야기
        } else {
          setPage(seg.pages.length - 1);
          setPhase("choices");  // 선택지는 아이가 누를 때만 읽는다
        }
        return;
      }
      if (saved.story.voice.provider === "browser") {
        // 서버 음성 한도가 없을 때: 처음부터 끝까지 브라우저 음성
        setPhase("playing");
        const from = startAt.current ?? 0;
        startAt.current = null;
        for (let i = from; i < seg.pages.length; i++) {
          if (!isCurrent(t)) return;
          setPage(i);
          await speak(seg.pages[i].text, 0.95 * getRate());
        }
        finish();
        return;
      }
      let mp3 = await getAudio(saved.story.id, view);
      if (!mp3) {
        try {
          mp3 = await loadAudio(saved, view);
        } catch (e) {
          startAt.current = null;
          // 왜 못 받았는지 서버 기록에 남긴다 (Gemini 한도 429 → 서버 502 tts_failed, 서버 구간당 한도 429 tts_limit 등)
          sendEvent(getAnonId(), "voice_failed", saved.story.id,
                    { index: view, reason: e instanceof ApiError ? `server:${e.status}:${e.code}` : "network" });
          if (isCurrent(t)) setPhase("manual");  // 음성 실패: 글만 보여 주고 버튼으로 넘김
          return;
        }
      }
      const audio = player;
      if (!isCurrent(t) || !audio) return;  // 기다리는 동안 화면을 떠났으면 재생하지 않음
      const url = URL.createObjectURL(mp3);
      audio.src = url;
      audio.playbackRate = getRate();
      audio.volume = getVoiceVolume();  // 앞 구간 끝에서 0으로 줄여 둔 음량을 재생 직전에 되돌린다
      let starts = [0];
      audio.onloadedmetadata = () => {
        starts = pageStartTimes(seg.pages.map((p) => p.text), audio.duration);
        if (startAt.current !== null) {  // 이어 듣기: 저장된 쪽부터
          const i = Math.min(startAt.current, seg.pages.length - 1);
          startAt.current = null;
          audio.currentTime = starts[i];
          setPage(i);
        }
      };
      audio.ontimeupdate = () => { if (isCurrent(t)) setPage(pageAt(audio.currentTime, starts)); };
      // 끝나기 조금 전부터 소리를 줄이고 일찍 멈춘다 (끝의 '콱' 소리 방지, audio.ts)
      stopWatch = watchEnd(audio, () => { URL.revokeObjectURL(url); finish(); });
      audio.play().then(() => { if (isCurrent(t)) setPhase("playing"); })
        .catch((e: unknown) => {
          // 받았는데 재생이 막힘 (아이폰 자동 재생 제한 NotAllowedError, 파일 손상 NotSupportedError 등)
          sendEvent(getAnonId(), "voice_failed", saved.story.id,
                    { index: view, reason: `play:${e instanceof Error ? e.name : "unknown"}` });
          if (isCurrent(t)) setPhase("manual");
        });
    }
    run();
    // 화면을 떠나면(또는 구간이 바뀌면) 재생을 멈춘다
    return () => { stopWatch(); if (isCurrent(t)) stopAll(); };
  }, [view, restart]);  // eslint-disable-line react-hooks/exhaustive-deps

  // 페이지가 바뀔 때: 분위기에 맞는 음악(같은 곡이면 끊지 않고 이어서) + 그 페이지 효과음 1번
  useEffect(() => {
    const p = shown;
    playBgm(pickBgm(BGM, p.mood, isEnding, storyRng(saved.story.id)));
    playSfx(p.sfx);
    if (replaying.current) savePosition(saved.story.id, { view, page });  // 다시 듣는 위치 기억
  }, [view, page]);  // eslint-disable-line react-hooks/exhaustive-deps

  // 이야기 음성이 나오는 동안 음악을 작게
  useEffect(() => { duckBgm(phase === "playing" && !paused); }, [phase, paused]);

  // 새 쪽이 나오면 그 글이 보이게 (앞 쪽 글은 위에 남는다)
  useEffect(() => { textEnd.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" }); }, [view, page]);

  // 읽기 화면을 떠나면 음악·효과음을 끈다 (빈 목록 [] → 화면이 처음 생길 때 한 번, 반환 함수는 떠날 때)
  useEffect(() => () => stopSound(), []);

  // 구간 하나를 다 읽은 뒤 (음성이 끝났거나, 음성 없이 마지막 쪽에서 "다음"을 눌렀을 때)
  function afterSegment() {
    if (replaying.current && view < last) {
      setView(view + 1);  // 다시 듣기: 다음 구간으로 (지난 선택지는 보여 주지 않음)
    } else if (isEnding) {
      if (!replaying.current) sendEvent(getAnonId(), "complete", saved.story.id);
      replaying.current = false;
      clearPosition(saved.story.id);  // 끝까지 들었으니 이어 들을 곳 없음
      setPhase("end");
    } else {
      setPhase("choices");  // 선택지는 아이가 누를 때만 읽는다 (어차피 두 번 눌러야 고름)
    }
  }

  function nextPage() {
    if (page < seg.pages.length - 1) setPage(page + 1);
    else afterSegment();
  }

  async function request(s: SavedStory) {
    setPhase("waiting");
    if (requesting.current) return;  // 같은 요청이 이미 가는 중 (두 번 보내면 구간당 2번 한도를 씀)
    requesting.current = true;
    pending.current = s;
    try {
      const { story, history, chosen } = nextArgs(s);
      const res = await nextSegment(getAnonId(), story, history, chosen);
      const updated = addSegment(s, res, s.createdAt);
      await saveStory(updated);
      resuming.current = false;
      onUpdate(updated);
      setView(updated.segments.length - 1);
    } catch (e) {
      setProblem(e instanceof ApiError ? e.code : "unknown");
      setPhase("problem");
    } finally {
      requesting.current = false;
    }
  }

  function tapChoice(c: Choice) {
    if (focus !== c.id) {  // 첫 터치: 읽어 주기
      setFocus(c.id);
      speak(c.label);
      return;
    }
    const s = choose(saved, c.id);
    saveStory(s);
    onUpdate(s);
    request(s);
  }

  // 다시 듣기 시작: 처음부터 또는 저장된 위치부터
  function replayFrom(pos: { view: number; page: number }) {
    resuming.current = false;
    replaying.current = true;
    startAt.current = pos.page > 0 ? pos.page : null;
    if (pos.view === view) setRestart((n) => n + 1);
    else setView(pos.view);
  }

  // 다시 듣기 중 이전·다음 쪽: 그 쪽 위치부터 다시 재생 (구간 끝을 넘으면 앞·뒤 구간으로)
  function goPage(dir: 1 | -1) {
    const target = page + dir;
    if (target >= seg.pages.length) {
      if (view < last) replayFrom({ view: view + 1, page: 0 });
      else afterSegment();
    } else if (target < 0) {
      if (view > 0) replayFrom({ view: view - 1, page: saved.segments[view - 1].segment.pages.length - 1 });
    } else {
      replayFrom({ view, page: target });
    }
  }

  // 잠깐 멈추기 / 이어서 듣기 (이야기 목소리와 자동 페이지 넘김이 같이 멈춘다)
  function togglePause() {
    if (paused) {
      player?.play().catch(() => {});
      if (typeof speechSynthesis !== "undefined") speechSynthesis.resume();
    } else {
      player?.pause();
      if (typeof speechSynthesis !== "undefined") speechSynthesis.pause();
    }
    setPaused(!paused);
  }

  function toggleMute() {
    setMuted(!muted);
    setMutedState(!muted);
  }

  // 다 들은 이야기를 책장에서 열었을 때만 '이어 듣기' 를 보여 준다
  const resumePos = phase === "end" && resume ? getPosition(saved.story.id) : null;

  const listening = phase === "playing" || phase === "loading" || phase === "manual";
  const canNavigate = replaying.current && listening;  // 다 만든 이야기를 다시 들을 때만 이전·다음
  const pageIndex = Math.min(page, seg.pages.length - 1);
  if (phase === "problem") return <Problem code={problem} onRetry={() => request(pending.current!)} onHome={onHome} />;

  return (
    <main className="reading">
      <header className="reading-top">
        <button className="icon-button" onClick={onHome} aria-label="처음으로">🏠</button>
        <span className="reading-step">{view + 1} / {saved.story.choice_count + 1}</span>
        <div className="reading-tools">
          {/* 음소거: 음악·효과음만 끔. 이야기 목소리는 계속 */}
          {phase === "playing" && (
            <button className="icon-button" onClick={togglePause} aria-label={paused ? "이어서 듣기" : "잠깐 멈추기"}>
              {paused ? "▶️" : "⏸️"}
            </button>
          )}
          <button className="icon-button" onClick={toggleMute} aria-label={muted ? "음악 켜기" : "음악 끄기"}>
            {muted ? "🔇" : "🎵"}
          </button>
          <button className="icon-button" onClick={() => setSettingsOpen(true)} aria-label="설정">⚙️</button>
        </div>
      </header>

      {/* 세로 화면: 위 버튼 → 장면 → 글·선택지 순서로 한 줄. 가로 화면: 왼쪽 장면, 오른쪽 위 버튼·글·선택지 (Reading.css) */}
      <div className="reading-stage">
        <Scene scene={shown.scene} placed />
        {/* 다음 이야기를 만드는 동안: 화면은 그대로 두고 장면 위에 살짝 덮어 알려 준다 */}
        {phase === "waiting" && (
          <div className="making" role="status">
            <span className="making-emoji">{emojiOf(shown.scene.characters[0]?.id ?? saved.story.cards[0])}</span>
            <span>다음 이야기를 만들고 있어요</span>
            <span className="making-dots"><i /><i /><i /></span>
          </div>
        )}
      </div>

      <div className="reading-body">
      {/* 읽은 쪽 글은 지우지 않고 아래로 이어 붙인다 (빨리 넘어가도 다시 읽을 수 있게) */}
      <div className="reading-text">
        {seg.pages.slice(0, pageIndex + 1).map((p, i) => (
          <p key={`${view}-${i}`} ref={i === pageIndex ? textEnd : undefined} className={i === pageIndex ? "now" : "past"}>{p.text}</p>
        ))}
        {/* 목소리 안내는 글 바로 아래에 */}
        {phase === "loading" && <p className="voice-note">🔊 목소리를 준비하고 있어요</p>}
        {/* 음성을 못 받았거나(무료 한도·오류) 재생이 막혔을 때: 글만 보여 주고 버튼으로 넘긴다 */}
        {phase === "manual" && <p className="voice-note">🔇 목소리를 불러오지 못했어요. 버튼을 눌러 넘겨 주세요</p>}
      </div>
      {canNavigate ? (
        <div className="page-nav">
          <button className="big-button soft" onClick={() => goPage(-1)} aria-label="이전 쪽" disabled={view === 0 && pageIndex === 0}>◀ 이전</button>
          <button className="big-button soft" onClick={() => goPage(1)} aria-label="다음 쪽">다음 ▶</button>
        </div>
      ) : phase === "manual" && <button className="big-button" onClick={nextPage}>다음 ▶</button>}

      {phase === "choices" && (
        <div className={`choices ${seg.choices[0]?.kind === "phrase" ? "phrases" : ""}`}>
          {seg.choices.map((c) => (
            <button key={c.id} className={`choice${focus === c.id ? " focus" : ""}`} onClick={() => tapChoice(c)}>
              {c.kind === "item" && <span className="choice-emoji"><Picture id={c.id} size={64} /></span>}
              <span className="choice-label">{c.label}</span>
            </button>
          ))}
          <p className="reading-status">{focus ? "한 번 더 누르면 골라요" : "무엇이 나올까요?"}</p>
        </div>
      )}

      {phase === "end" && (
        <div className="ending">
          <p className="ending-title">🌟 끝 🌟</p>
          {resumePos && <button className="big-button" onClick={() => replayFrom(resumePos)}>▶ 이어 듣기</button>}
          <button className={`big-button${resumePos ? " soft" : ""}`} onClick={() => replayFrom({ view: 0, page: 0 })}>🔁 처음부터 다시 듣기</button>
          <button className="big-button soft" onClick={onNew}>✨ 새 이야기</button>
        </div>
      )}
      </div>
      {settingsOpen && <Settings onClose={() => setSettingsOpen(false)} />}
    </main>
  );
}

import { useEffect, useState } from "react";
import { getDemoVoices, getStoryVoice, setStoryVoice, STORY_VOICES } from "../api";
import { getGuideVoice, getRate, getVoiceVolume, playVoicePreview, setGuideVoice, setRate, setVoiceVolume, speak, stepRate,
         stopVoicePreview } from "../audio";
import type { GuideVoice } from "../audio";
import { getMusicVolume, setMusicVolume } from "../sound";
import "./Settings.css";

type Props = { onClose: () => void };

const GUIDE_VOICES: [GuideVoice, string][] = [["female", "여성"], ["male", "남성"]];

// 설정 창 (부모용): 소리 크기, 읽는 빠르기, 안내 목소리. 모두 기기에 저장된다
// 폰은 아래에서 올라오는 시트, PC(≥1024px)는 가운데 대화상자 (Settings.css)
export default function Settings({ onClose }: Props) {
  const [music, setMusic] = useState(getMusicVolume());
  const [voiceVol, setVoiceVol] = useState(getVoiceVolume());
  const [rate, setRateState] = useState(getRate());
  const [guide, setGuide] = useState(getGuideVoice());
  const [storyVoice, setStoryVoiceState] = useState(getStoryVoice());
  const [demoVoices, setDemoVoices] = useState<[string, string][]>([]);
  // 창이 열리면 서버에 시연용 목소리가 있는지 묻는다 (없으면 기본 목소리만)
  useEffect(() => { getDemoVoices().then(setDemoVoices); }, []);

  const close = () => { stopVoicePreview(); onClose(); };
  // 크레파스 슬라이더: --p(채워진 비율)로 트랙 앞부분을 노랗게 칠한다
  const fill = (v: number) => ({ "--p": `${Math.round(v * 100)}%` } as React.CSSProperties);

  return (
    // 바깥(어두운 곳)을 누르면 닫힘. 안쪽을 누를 때는 닫히지 않게 전달을 막는다(stopPropagation)
    <div className="settings-backdrop" onClick={close}>
      <section className="settings" role="dialog" aria-label="설정" onClick={(e) => e.stopPropagation()}>
        <h2 className="display">설정</h2>

        <div className="settings-row">
          <label className="settings-head" htmlFor="set-music">
            <span>🎵 음악·효과음</span>
            <output className="display">{Math.round(music * 100)}</output>
          </label>
          <input id="set-music" className="crange" type="range" min={0} max={100} value={Math.round(music * 100)} style={fill(music)}
                 onChange={(e) => { const v = Number(e.target.value) / 100; setMusic(v); setMusicVolume(v); }} />
        </div>

        <div className="settings-row">
          <label className="settings-head" htmlFor="set-voice">
            <span>🗣️ 목소리</span>
            <output className="display">{Math.round(voiceVol * 100)}</output>
          </label>
          <input id="set-voice" className="crange" type="range" min={0} max={100} value={Math.round(voiceVol * 100)} style={fill(voiceVol)}
                 onChange={(e) => { const v = Number(e.target.value) / 100; setVoiceVol(v); setVoiceVolume(v); }} />
        </div>

        <div className="settings-row">
          <span className="settings-head">⏩ 읽는 빠르기</span>
          <div className="settings-rate">
            <button onClick={() => { const r = stepRate(rate, -1); setRate(r); setRateState(r); }} aria-label="더 느리게">−</button>
            <span className="display">{rate.toFixed(1)}배</span>
            <button onClick={() => { const r = stepRate(rate, 1); setRate(r); setRateState(r); }} aria-label="더 빠르게">+</button>
          </div>
        </div>

        <div className="settings-row">
          <span className="settings-head">📖 이야기 목소리</span>
          <div className="settings-chips">
            {[...STORY_VOICES, ...demoVoices].map(([v, label]) => (
              <button key={v} className={storyVoice === v ? "on" : ""} aria-pressed={storyVoice === v}
                      onClick={() => { setStoryVoice(v); setStoryVoiceState(v); if (v) playVoicePreview(v); else stopVoicePreview(); }}>
                {label}
              </button>
            ))}
          </div>
          <span className="settings-hint">누르면 미리 들려줘요. 새 이야기부터 바뀌고, 무료 한도를 다 쓰면 다른 목소리로 읽어요</span>
        </div>

        <div className="settings-row">
          <span className="settings-head">📢 안내 목소리</span>
          <div className="settings-chips">
            {GUIDE_VOICES.map(([v, label]) => (
              <button key={v} className={guide === v ? "on" : ""} aria-pressed={guide === v}
                      onClick={() => { setGuideVoice(v); setGuide(v); speak("이야기의 주인공은 누구일까요?"); }}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <button className="big-button" onClick={close}>닫기</button>
      </section>
    </div>
  );
}

import { useState } from "react";
import { getTtsPause, setTtsPause } from "../api";
import { getGuideVoice, getRate, getVoiceVolume, setGuideVoice, setRate, setVoiceVolume, speak, stepRate } from "../audio";
import type { GuideVoice } from "../audio";
import { getMusicVolume, setMusicVolume } from "../sound";
import "./Settings.css";

// onRegenerate: (실험) 지금 구간 음성을 다시 만들기. 읽기 화면에서만 넘긴다
type Props = { onClose: () => void; onRegenerate?: () => void };

const GUIDE_VOICES: [GuideVoice, string][] = [["female", "여성"], ["male", "남성"]];

// 설정 창 (부모용): 소리 크기, 읽는 빠르기, 안내 목소리. 모두 기기에 저장된다
export default function Settings({ onClose, onRegenerate }: Props) {
  const [music, setMusic] = useState(getMusicVolume());
  const [voiceVol, setVoiceVol] = useState(getVoiceVolume());
  const [rate, setRateState] = useState(getRate());
  const [guide, setGuide] = useState(getGuideVoice());
  const [pause, setPause] = useState(getTtsPause());

  return (
    // 바깥(어두운 곳)을 누르면 닫힘. 안쪽을 누를 때는 닫히지 않게 전달을 막는다(stopPropagation)
    <div className="settings-backdrop" onClick={onClose}>
      <section className="settings" role="dialog" aria-label="설정" onClick={(e) => e.stopPropagation()}>
        <h2>설정</h2>

        <label className="settings-row">
          <span>🎵 음악·효과음</span>
          <input type="range" min={0} max={100} value={Math.round(music * 100)}
                 onChange={(e) => { const v = Number(e.target.value) / 100; setMusic(v); setMusicVolume(v); }} />
          <span className="settings-value">{Math.round(music * 100)}</span>
        </label>

        <label className="settings-row">
          <span>🗣️ 목소리</span>
          <input type="range" min={0} max={100} value={Math.round(voiceVol * 100)}
                 onChange={(e) => { const v = Number(e.target.value) / 100; setVoiceVol(v); setVoiceVolume(v); }} />
          <span className="settings-value">{Math.round(voiceVol * 100)}</span>
        </label>

        <div className="settings-row">
          <span>⏩ 읽는 빠르기</span>
          <div className="settings-rate">
            <button onClick={() => { const r = stepRate(rate, -1); setRate(r); setRateState(r); }} aria-label="더 느리게">−</button>
            <span>{rate.toFixed(1)}배</span>
            <button onClick={() => { const r = stepRate(rate, 1); setRate(r); setRateState(r); }} aria-label="더 빠르게">+</button>
          </div>
        </div>

        <div className="settings-row">
          <span>📢 안내 목소리</span>
          <div className="settings-chips">
            {GUIDE_VOICES.map(([v, label]) => (
              <button key={v} className={guide === v ? "on" : ""}
                      onClick={() => { setGuideVoice(v); setGuide(v); speak("이야기의 주인공은 누구일까요?"); }}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="settings-lab">
          <p>(실험) 문장 사이 쉼</p>
          <div className="settings-row">
            <input type="number" min={0.2} max={3} step={0.1} value={pause ?? ""} placeholder="짧게(기본)"
                   onChange={(e) => { const v = e.target.value ? Number(e.target.value) : null; setPause(v); setTtsPause(v); }} />
            <span>초</span>
            {onRegenerate && <button onClick={() => { onRegenerate(); onClose(); }}>이 구간 음성 다시 만들기</button>}
          </div>
          <p className="settings-note">서버는 같은 구간 음성을 2번까지만 만들고, Gemini 음성은 모델당 하루 10회입니다.</p>
        </div>

        <button className="big-button" onClick={onClose}>닫기</button>
      </section>
    </div>
  );
}

import { useState } from "react";
import type { Page } from "../api";
import { emojiOf } from "../catalog";
import { actorSlots, stateMark, timeFilter } from "../scene";
import Picture from "./Picture";
import "./Scene.css";

type Props = { scene: Page["scene"] };

// 한 페이지의 장면: 배경 그림 + 시간대 필터 + 캐릭터·사물 배치 + 상태 표시
export default function Scene({ scene }: Props) {
  // 캐릭터 먼저, 남는 자리에 사물 (최대 4개)
  const actors = [
    ...scene.characters.map((c) => ({ id: c.id, mark: stateMark(c.state), object: false })),
    ...scene.objects.map((id) => ({ id, mark: null, object: true })),
  ];
  const slots = actorSlots(actors.length);

  return (
    <section className={`scene bg-${scene.background}`} aria-hidden="true">
      {/* key: 배경이 바뀌면 새 요소로 만들어 '불러오기 실패' 기억을 지운다 */}
      <Backdrop key={scene.background} id={scene.background} filter={timeFilter(scene.time)} />
      {slots.map((slot, i) => {
        const actor = actors[i];
        return (
          <div
            key={`${i}-${actor.id}`}
            className={`actor${actor.object ? " object" : ""}`}
            style={{
              left: `${slot.left}%`,
              bottom: `${slot.bottom}%`,
              width: `${(actor.object ? 22 : 32) * slot.scale}%`,
              animationDelay: `${i * 0.6}s`,
            }}
          >
            {actor.mark && <span className="state-mark">{actor.mark}</span>}
            <Picture id={actor.id} />
          </div>
        );
      })}
    </section>
  );
}

// 배경 그림. 없으면 지금처럼 배경색 + 구석 이모지
function Backdrop({ id, filter }: { id: string; filter: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return <span className="scene-bg">{emojiOf(id)}</span>;
  return (
    <img className="scene-backdrop" src={`/img/${id}.webp`} alt="" style={{ filter }}
         onError={() => setFailed(true)} />
  );
}

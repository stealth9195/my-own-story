import { useState } from "react";
import type { Page } from "../api";
import { emojiOf, facingOf } from "../catalog";
import { actorSlots, arrangeActors, stateMark, timeFilter } from "../scene";
import Picture from "./Picture";
import "./Scene.css";

type Props = { scene: Page["scene"] };

// 한 페이지의 장면: 배경 그림 + 시간대 색 + 캐릭터·사물 배치(서로 마주 보게) + 상태 표시
export default function Scene({ scene }: Props) {
  const actors = arrangeActors(scene.characters.map((c) => ({ ...c, facing: facingOf(c.id) })), scene.objects);
  const slots = actorSlots(actors.length);

  return (
    <section className={`scene bg-${scene.background} time-${scene.time}`} aria-hidden="true">
      {/* key: 배경이 바뀌면 새 요소로 만들어 '불러오기 실패' 기억을 지운다 */}
      <Backdrop key={scene.background} id={scene.background} filter={timeFilter(scene.time)} />
      {/* 밤·노을: 배경에 색을 덮는다 (캐릭터는 아이가 알아보기 쉽게 그대로, 낮은 투명) */}
      <div className="scene-tint" />
      {slots.map((slot, i) => {
        const actor = actors[i];
        const mark = actor.state ? stateMark(actor.state) : null;
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
            {/* 상태 표시는 뒤집는 그림 바깥에, 바라보는 쪽 머리 위에 (안에 두면 글자도 거울처럼 뒤집힘) */}
            {mark && <span className={`state-mark ${actor.looks === "left" ? "on-left" : "on-right"}`}>{mark}</span>}
            <div className={actor.flip ? "flip" : undefined}><Picture id={actor.id} /></div>
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

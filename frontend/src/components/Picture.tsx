import { useState } from "react";
import { emojiOf } from "../catalog";
import "./Picture.css";

// size: 가로세로 px. 없으면 부모 칸을 채운다(장면 안에서 화면 폭에 맞출 때)
type Props = { id: string; size?: number };

// 그림(img/{id}.webp)이 있으면 그림, 불러오지 못하면 이모지로 바꾼다
// → 아직 안 만든 그림이 있어도 화면이 깨지지 않는다
export default function Picture({ id, size }: Props) {
  // useState: 이 그림을 못 불러왔는지 기억. 바뀌면 화면을 다시 그린다
  const [failed, setFailed] = useState(false);
  const box = size ? { width: size, height: size } : undefined;

  if (failed) {
    return (
      <span className="picture picture-emoji" style={{ ...box, fontSize: size ? size * 0.8 : undefined }}>
        {emojiOf(id)}
      </span>
    );
  }
  return (
    <img className="picture" src={`/img/${id}.webp`} alt="" style={box} draggable={false}
         onError={() => setFailed(true)} />
  );
}

// 책장 저장. 서버는 이야기를 저장하지 않으므로 이 기기의 IndexedDB 에 둔다.
// idb-keyval: IndexedDB 를 get/set 처럼 간단히 쓰게 해 주는 작은 라이브러리
// 저장이 안 되는 환경(사파리 비공개 모드 등)에서도 이야기는 계속되도록 오류는 모두 무시한다.
import { del, entries, get, keys, set } from "idb-keyval";
import type { SignedSegment, StoryKey } from "./api";

export type SavedStory = {
  story: StoryKey;
  segments: SignedSegment[];   // 서버가 서명한 구간 (다음 요청에 그대로 보냄)
  chosen: string[];            // 지금까지 고른 선택지 id
  createdAt: number;
  done: boolean;
  favorite?: boolean;          // 책장에서 하트로 표시한 이야기 (예전에 저장한 이야기에는 없음)
};

const storyKey = (id: string) => `story:${id}`;
const audioKey = (id: string, index: number) => `audio:${id}:${index}`;

async function quiet<T>(work: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await work();
  } catch {
    return fallback;
  }
}

export function saveStory(s: SavedStory): Promise<void> {
  return quiet(() => set(storyKey(s.story.id), s), undefined);
}

export function getStory(id: string): Promise<SavedStory | undefined> {
  return quiet(() => get<SavedStory>(storyKey(id)), undefined);
}

export async function listStories(): Promise<SavedStory[]> {
  const all = await quiet(() => entries<string, SavedStory>(), []);
  return all.filter(([k]) => String(k).startsWith("story:")).map(([, v]) => v)
    .sort((a, b) => b.createdAt - a.createdAt);
}

export function saveAudio(storyId: string, index: number, mp3: Blob): Promise<void> {
  return quiet(() => set(audioKey(storyId, index), mp3), undefined);
}

export function getAudio(storyId: string, index: number): Promise<Blob | undefined> {
  return quiet(() => get<Blob>(audioKey(storyId, index)), undefined);
}

// 음성은 최근 keep 편만 남긴다 (이야기 글은 그대로)
export async function pruneAudio(keep = 20): Promise<void> {
  const old = new Set((await listStories()).slice(keep).map((s) => s.story.id));
  if (old.size === 0) return;
  const all = await quiet(() => keys<string>(), []);
  const targets = all.filter((k) => String(k).startsWith("audio:") && old.has(String(k).split(":")[1]));
  await Promise.all(targets.map((k) => quiet(() => del(k), undefined)));
}

// 책장에서 지우기: 이야기와 그 이야기의 음성을 모두 지운다 (다른 이야기는 그대로)
export async function deleteStory(id: string): Promise<void> {
  const all = await quiet(() => keys<string>(), []);
  const targets = all.filter((k) => String(k) === storyKey(id) || String(k).startsWith(`audio:${id}:`));
  await Promise.all(targets.map((k) => quiet(() => del(k), undefined)));
}

let memoryAnonId: string | null = null;

// 기기별 익명 ID (로그인 없음). localStorage 를 못 쓰면 이번 실행 동안만 쓰는 값
export function getAnonId(): string {
  try {
    let id = localStorage.getItem("anon_id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("anon_id", id);
    }
    return id;
  } catch {
    memoryAnonId ??= crypto.randomUUID();
    return memoryAnonId;
  }
}

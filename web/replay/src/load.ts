import { HASH, validateIndex, validateRecording, type Entry, type Index } from "./contracts.js";

export function evidenceBase(base: string, origin: string): URL {
  const url = new URL(base, origin);
  if (url.origin !== new URL(origin).origin || url.username || url.password || url.search || url.hash || !url.pathname.endsWith("/")) throw Error("Evidence requires a same-origin directory");
  return url;
}
export async function readVerified(url: URL, hash: string, signal: AbortSignal, limit: number): Promise<unknown> {
  if (!HASH.test(hash)) throw Error("Invalid evidence checksum");
  const response = await fetch(url, { signal, credentials: "omit", redirect: "error", cache: "no-cache" });
  if (!response.ok || !response.body) throw Error("Evidence unavailable");
  const reader = response.body.getReader(), chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) throw Error("Evidence exceeds size limit");
      chunks.push(value);
    }
  } finally { await reader.cancel(); reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const actual = Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, "0")).join("");
  if (actual !== hash) throw Error("Evidence checksum mismatch");
  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
}
export async function loadIndex(base: URL, hash: string, signal: AbortSignal) {
  return validateIndex(await readVerified(new URL("index.json", base), hash, signal, 65536));
}
export async function loadRecording(base: URL, index: Index, entry: Entry, signal: AbortSignal) {
  const values = await Promise.all(["replay", "manifest", "metrics", "events"].map(name => {
    const path = `${entry.run_id}/${name}.json`;
    return readVerified(new URL(path, base), index.checksums[path], signal, name === "replay" ? 4 * 1024 * 1024 : 65536);
  }));
  return validateRecording(entry, ...values as [unknown, unknown, unknown, unknown]);
}

import test from "node:test";
import assert from "node:assert/strict";
import { Quaternion, Vector3 } from "three";
import { renderToString } from "react-dom/server";
import { createElement } from "react";
import { enuToView, sampleAt, slerp, validateIndex } from "../dist/contracts.js";
import { evidenceBase, readVerified } from "../dist/load.js";
import { ReplayViewer } from "../dist/index.js";
const samples = [{ time_s: 0, position_m: [0, 0, 1], target_m: [0, 0, 1], quaternion_wxyz: [1, 0, 0, 0] }, { time_s: 1, position_m: [1, 0, 1], target_m: [0, 1, 1], quaternion_wxyz: [Math.SQRT1_2, 0, 0, Math.SQRT1_2] }];
test("frame basis preserves gravity, north and body-to-world yaw", () => {
  assert.deepEqual(enuToView([1, 2, 3]), [1, 3, -2]);
  const basis = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), -Math.PI / 2);
  const yaw = new Quaternion(0, 0, Math.SQRT1_2, Math.SQRT1_2);
  assert.ok(new Vector3(1, 0, 0).applyQuaternion(basis.clone().multiply(yaw)).distanceTo(new Vector3(0, 0, -1)) < 1e-12);
  const roll = new Quaternion(Math.SQRT1_2, 0, 0, Math.SQRT1_2);
  assert.ok(new Vector3(0, 0, 1).applyQuaternion(basis.clone().multiply(roll)).distanceTo(new Vector3(0, 0, 1)) < 1e-12);
});
test("interpolation clamps endpoints, holds target steps and takes shortest quaternion arc", () => {
  const mid = sampleAt(samples, .5);
  assert.deepEqual(mid.position_m, [.5, 0, 1]); assert.deepEqual(mid.target_m, [0, 0, 1]);
  assert.ok(Math.abs(mid.quaternion_wxyz[0] - Math.cos(Math.PI / 8)) < 1e-12);
  assert.deepEqual(sampleAt(samples, 1).target_m, [0, 1, 1]);
  assert.deepEqual(sampleAt(samples, -5).position_m, [0, 0, 1]);
  assert.deepEqual(sampleAt(samples, 9).position_m, [1, 0, 1]);
  assert.deepEqual(slerp([1, 0, 0, 0], [-1, 0, 0, 0], .5), [1, 0, 0, 0]);
  assert.throws(() => sampleAt(samples, NaN));
});
test("SSR renders a paused accessible shell without browser or GPU access", () => {
  const html = renderToString(createElement(ReplayViewer, { baseUrl: "/evidence/", indexSha256: "a".repeat(64) }));
  assert.match(html, /RECORDED SIMULATION/); assert.match(html, /Play replay/); assert.doesNotMatch(html, /<canvas/);
});
test("evidence paths stay same-origin without credentials or redirection", () => {
  assert.equal(evidenceBase("/evidence/", "https://example.org/work/").href, "https://example.org/evidence/");
  const credentialUrl = new URL("https://example.org/"); credentialUrl.username = "name";
  for (const path of ["https://example.net/", "//example.net/", "/evidence?x=y", "/evidence/#hash", credentialUrl.href]) assert.throws(() => evidenceBase(path, "https://example.org/"));
  assert.throws(() => validateIndex({ schema_version: 1, runs: [{ run_id: "../private" }] }));
});
test("streaming reader rejects oversized and changed content", async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response("12345");
    await assert.rejects(readVerified(new URL("https://example.org/"), "a".repeat(64), new AbortController().signal, 4), /size limit/);
    await assert.rejects(readVerified(new URL("https://example.org/"), "a".repeat(64), new AbortController().signal, 20), /checksum mismatch/);
  } finally { globalThis.fetch = previous; }
});

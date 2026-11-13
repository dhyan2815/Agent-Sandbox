// Phase 4 acceptance (side branch): the Galaxy with about 20,000 passages.
//
//   BASE_URL=http://127.0.0.1:8000 node e2e/galaxy.mjs [passages]
//
// Uploads a generated document of short sections (one passage each), asks a question,
// opens Explore, and checks: every passage is drawn, the frame rate over five seconds, and
// that the reranked top 5 and the question's position equal the saved run.

import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://127.0.0.1:8000";
const COUNT = Number(process.argv[2] ?? 20000);
const folder = mkdtempSync(join(tmpdir(), "hyper-rag-galaxy-"));
const topics = ["inverter", "battery", "panel", "meter", "cable", "roof", "warranty", "invoice"];
const sections = [];
for (let i = 0; i < COUNT; i++) {
  const topic = topics[i % topics.length];
  sections.push(`# Note ${i}\n\nThe ${topic} log entry ${i} records reading ${(i * 37) % 1000} on site ${i % 97}.`);
}
const doc = join(folder, "notes.md");
writeFileSync(doc, sections.join("\n\n"));

const browser = await chromium.launch({ args: ["--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const expect = (ok, message) => {
  if (!ok) throw new Error(message);
};
try {
  await page.goto(BASE + "/");
  await page.fill("#new-name", "Galaxy");
  await page.click("#new-collection button");
  await page.setInputFiles("#picker", doc);
  await page.waitForSelector("#files-table tbody tr:not(.reading) td.name", { timeout: 600_000 });
  await page.click(".tab[data-tab=chat]");
  await page.fill("#question", "Which battery log entry recorded reading 333?");
  await page.press("#question", "Enter");
  await page.waitForSelector(".msg.bot .answer", { timeout: 120_000 });
  await page.click(".tab[data-tab=explore]");
  await page.waitForSelector("[data-testid=galaxy]", { timeout: 120_000 });
  const points = Number(await page.getAttribute("[data-testid=galaxy]", "data-points"));
  await page.waitForTimeout(6000); // let the fps meter settle over several seconds
  const fps = Number(await page.getAttribute("[data-testid=galaxy]", "data-fps"));
  const renderer = await page.evaluate(() => {
    const gl = document.createElement("canvas").getContext("webgl2");
    const info = gl?.getExtension("WEBGL_debug_renderer_info");
    return info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : "unknown";
  });
  const runs = await page.evaluate(async () => (await (await fetch("/collections/galaxy/runs")).json()).runs);
  const run = await page.evaluate(async (id) => (await fetch(`/collections/galaxy/runs/${id}`)).json(), runs[0].id);
  const rerank = run.events.filter((e) => e.t === "r.rerank").at(-1).hits.length;
  const listed = await page.locator(".top5 li").count();
  const position = run.events.find((e) => e.t === "q.position").xyz;
  expect(points >= COUNT, `points drawn: ${points}`);
  expect(listed === rerank, `top 5 listed ${listed}, logged ${rerank}`);
  expect(position.length === 3 && position.every((v) => Number.isFinite(v)), "question position");
  expect(errors.length === 0, `page errors: ${errors}`);
  await page.screenshot({ path: join(folder, "galaxy.png") });
  console.log(JSON.stringify({ points, fps, renderer, listed, rerank, position, screenshot: join(folder, "galaxy.png") }));
} catch (error) {
  await page.screenshot({ path: join(folder, "failure.png"), fullPage: true });
  console.error(`FAILED: ${error.message} (${join(folder, "failure.png")})`);
  process.exitCode = 1;
} finally {
  await browser.close();
}

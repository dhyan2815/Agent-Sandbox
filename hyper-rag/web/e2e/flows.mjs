// End-to-end check that the React app covers every flow of the classic page.
//
//   BASE_URL=http://127.0.0.1:8000 [E2E_PASSWORD=...] node e2e/flows.mjs
//
// Needs a running server in offline mode (HYPER_RAG_OFFLINE=1) with an empty data folder
// and the sample pack ingested. With E2E_PASSWORD it also logs in first and out at the end.

import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://127.0.0.1:8000";
const PASSWORD = process.env.E2E_PASSWORD;
const QUESTION = "How long does a standard rooftop installation take?";

const folder = mkdtempSync(join(tmpdir(), "hyper-rag-e2e-"));
const doc = join(folder, "install-guide.md");
writeFileSync(
  doc,
  "# Installation\n\nA standard rooftop installation takes two working days. " +
    "The crew arrives at eight in the morning.\n\n# Warranty\n\n" +
    "The inverter is covered by a ten year warranty from the date of installation.\n",
);

// A small PDF written by hand: one line of text per page, enough for the X-ray and the grid.
function makePdf(pages) {
  const objects = ["<< /Type /Catalog /Pages 2 0 R >>", null, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"];
  const kids = [];
  for (let n = 1; n <= pages; n++) {
    const text = `BT /F1 12 Tf 72 720 Td (Page ${n} says the inspection code is NW-${1000 + n}.) Tj ET`;
    objects.push(`<< /Length ${text.length} >>\nstream\n${text}\nendstream`);
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${objects.length} 0 R >>`);
    kids.push(`${objects.length} 0 R`);
  }
  objects[1] = `<< /Type /Pages /Kids [${kids.join(" ")}] /Count ${pages} >>`;
  let body = "%PDF-1.4\n";
  const offsets = [];
  objects.forEach((object, i) => {
    offsets.push(body.length);
    body += `${i + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = body.length;
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) body += `${String(offset).padStart(10, "0")} 00000 n \n`;
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return body;
}
const pdfPath = join(folder, "inspections.pdf");
writeFileSync(pdfPath, makePdf(40));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("dialog", (dialog) => dialog.accept()); // confirm() before deleting
const step = (name) => console.log(`ok  ${name}`);
const expect = (condition, message) => {
  if (!condition) throw new Error(message);
};

try {
  await page.goto(BASE + "/");
  if (PASSWORD) {
    await page.waitForURL("**/login");
    await page.fill("#password", PASSWORD);
    await page.click("button[type=submit]");
    await page.waitForURL(BASE + "/");
    step("logged in");
  }
  await page.waitForSelector("#root .nav");
  expect(await page.isVisible("#welcome"), "welcome screen shown with no collections");
  step("app loads from the React build");

  await page.fill("#new-name", "E2E docs");
  await page.click("#new-collection button");
  await page.waitForSelector(".tab.active[data-tab=files]");
  step("creating a collection opens its Files tab");

  await page.setInputFiles("#picker", doc);
  await page.waitForSelector("#queue .ok", { timeout: 60_000 });
  // Uploaded in parts; then read in the background while the table shows progress.
  await page.waitForSelector("#files-table tbody tr:not(.reading) td.name", { timeout: 60_000 });
  expect((await page.textContent("#files-table")).includes("install-guide.md"), "file listed");
  expect((await page.textContent("#subtitle")).startsWith("1 file"), "header counts the file");
  step("resumable upload, background read, parse report listed");

  await page.click(".tab[data-tab=chat]");
  await page.fill("#question", QUESTION);
  await page.press("#question", "Enter");
  await page.waitForSelector(".msg.bot .answer", { timeout: 60_000 });
  const answer = await page.textContent(".msg.bot .answer");
  expect(answer.includes("two working days"), `answer: ${answer}`);
  expect(await page.isVisible(".msg.bot details.trace"), "agent trace shown");
  step("question is answered with a citation");

  // Phase 3: every number on the strip and the waterfall comes from the saved event log.
  const runs = await page.evaluate(async () => (await (await fetch("/collections/e2e-docs/runs")).json()).runs);
  const run = await page.evaluate(
    async (id) => (await fetch(`/collections/e2e-docs/runs/${id}`)).json(),
    runs[0].id,
  );
  const stationMs = {};
  const stationOf = { "q.embed": "embed", "r.dense": "search", "r.bm25": "search", "r.fuse": "fuse",
    "r.rerank": "rerank", "a.grade": "grade", "a.rewrite": "rewrite", "a.generate": "generate",
    "a.check": "check", "q.condense": "condense" };
  for (const event of run.events) {
    const key = stationOf[event.t];
    if (key) stationMs[key] = (stationMs[key] ?? 0) + event.ms;
  }
  for (const [key, ms] of Object.entries(stationMs)) {
    const shown = Number(await page.getAttribute(`.metro [data-station=${key}]`, "data-ms"));
    expect(shown === Math.round(ms), `metro ${key}: shows ${shown}, log says ${ms}`);
  }
  await page.click(".msg.bot .waterfall summary");
  const rows = await page.$$eval(".waterfall tr[data-ms]", (trs) => trs.map((tr) => Number(tr.dataset.ms)));
  const logged = run.events.filter((e) => stationOf[e.t]).map((e) => e.ms);
  expect(JSON.stringify(rows) === JSON.stringify(logged), `waterfall ${rows} vs log ${logged}`);
  const latency = await page.evaluate(() => window.__hrLatency ?? []);
  expect(latency.length > 0 && Math.max(...latency) < 100, `event-to-screen latency ${latency}`);
  step(`strip and waterfall match the saved run; event-to-screen max ${Math.round(Math.max(...latency))} ms`);

  await page.click(".msg.bot .waterfall summary button:text('ranking')");
  await page.waitForSelector("[data-testid=rank-race] table");
  const fused = run.events.filter((e) => e.t === "r.fuse").at(-1).hits.length;
  const raceRows = await page.locator("[data-testid=rank-race] tbody tr").count();
  const kept = run.events.filter((e) => e.t === "a.grade").at(-1).kept;
  const keptRows = await page.$$eval("[data-testid=rank-race] tbody tr.kept", (trs) => trs.map((tr) => tr.dataset.runner));
  expect(raceRows === fused && JSON.stringify(keptRows.sort()) === JSON.stringify([...kept].sort()), "rank race matches the log");
  step("rank race shows every fused passage and the grader's choice");

  await page.click(".msg.bot .waterfall .replay");
  await page.waitForSelector(".metro .replaying");
  await page.waitForSelector(".metro .replaying", { state: "detached", timeout: 2000 }).catch(() => {});
  await page.waitForFunction(() => document.querySelector(".metro [data-station=check]")?.closest("li")?.classList.contains("done"), null, { timeout: 8000 });
  const replayed = Number(await page.getAttribute(".metro [data-station=generate]", "data-ms"));
  expect(replayed === Math.round(stationMs.generate), "replay ends on the same numbers");
  step("replay re-animates the strip from the saved run");

  await page.click(".msg.bot .answer .cite");
  await page.waitForSelector("#source-panel mark");
  expect((await page.textContent("#source-title")) === "install-guide.md", "source panel title");
  await page.keyboard.press("Escape");
  await page.waitForSelector("#source-panel", { state: "detached" });
  step("citation opens the source with the passage marked; Escape closes it");

  await page.fill("#question", "How long is that?");
  await page.press("#question", "Enter");
  await page.waitForFunction(() => document.querySelectorAll(".msg.bot .answer").length === 2, null, {
    timeout: 60_000,
  });
  await page.locator(".msg.bot details.trace").nth(1).click();
  const trace = await page.locator(".msg.bot details.trace").nth(1).textContent();
  expect(trace.includes("condense:"), `follow-up uses the conversation: ${trace}`);
  step("follow-up question is condensed with the conversation");

  await page.click("#new-chat");
  expect((await page.locator(".msg").count()) === 0, "new chat clears the thread");
  step("new chat clears the thread");

  // The page grid: a 40-page PDF, read in windows, one cell per page.
  await page.click(".tab[data-tab=files]");
  await page.setInputFiles("#picker", pdfPath);
  await page.waitForSelector("#files-table tr:not(.reading) a:text('inspections.pdf')", { timeout: 60_000 });
  await page.locator("tr", { hasText: "inspections.pdf" }).getByRole("button", { name: "Pages" }).click();
  await page.waitForSelector("[data-testid=page-grid] .cell.done");
  const cells = await page.locator("[data-testid=page-grid] .cells .cell").count();
  expect(cells === 40, `page grid has ${cells} cells`);
  step("page grid shows one cell per page");

  await page.click(".tab[data-tab=eval]");
  await page.fill("#eval-n", "2");
  await page.click("#eval-run");
  await page.waitForSelector("#eval-report table", { timeout: 120_000 });
  step("evaluation runs, polls and shows its report");

  await page.locator("#pack-list").getByRole("button", { name: "sample", exact: true }).click();
  expect((await page.locator(".tab").count()) === 1, "packs only have a Chat tab");
  await page.fill("#question", "Which header carries the webhook signature?");
  await page.press("#question", "Enter");
  await page.waitForSelector(".msg.bot .answer", { timeout: 60_000 });
  expect((await page.textContent(".msg.bot .answer")).includes("X-Lumen-Signature"), "pack answer");
  step("demo pack answers");

  await page.click("#collection-list .nav-item");
  await page.click(".tab[data-tab=files]");
  for (const name of ["inspections.pdf", "install-guide.md"]) {
    await page.locator("tr", { hasText: name }).getByRole("button", { name: "Remove" }).click();
    await page.waitForSelector(`#files-table a:text('${name}')`, { state: "detached" });
  }
  await page.waitForSelector("#files-table", { state: "detached" });
  step("removing the files empties the collection");

  await page.click("#delete-collection");
  await page.waitForSelector("#welcome");
  expect((await page.textContent("#collection-list")).includes("None yet"), "collection gone");
  step("deleting the collection returns to the welcome screen");

  // Reduced motion: the strip and charts change state without animating.
  const calm = await browser.newPage({ reducedMotion: "reduce" });
  if (PASSWORD) await calm.context().addCookies(await page.context().cookies());
  await calm.goto(BASE + "/");
  await calm.locator("#pack-list").getByRole("button", { name: "sample", exact: true }).click();
  const motion = await calm.evaluate(() => {
    const probe = document.createElement("div");
    probe.innerHTML = '<nav class="metro"><ol><li class="station active"><button><span class="dot"></span></button></li></ol></nav>';
    document.body.append(probe);
    const style = getComputedStyle(probe.querySelector(".dot"));
    return [style.transitionDuration, style.animationName];
  });
  expect(motion[0] === "0s" && motion[1] === "none", `reduced motion: ${motion}`);
  await calm.close();
  step("reduced-motion mode turns animation off");

  if (PASSWORD) {
    await page.click("#logout button");
    await page.waitForURL("**/login");
    step("logged out");
  }
  expect(errors.length === 0, `page errors: ${errors.join("; ")}`);
  console.log("all flows passed");
} catch (error) {
  await page.screenshot({ path: join(folder, "failure.png"), fullPage: true });
  console.error(`FAILED: ${error.message}\nscreenshot: ${join(folder, "failure.png")}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}

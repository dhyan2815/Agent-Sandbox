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
  expect((await page.textContent("#files-table")).includes("install-guide.md"), "file listed");
  expect((await page.textContent("#subtitle")).startsWith("1 file"), "header counts the file");
  step("upload is indexed and its parse report listed");

  await page.click(".tab[data-tab=chat]");
  await page.fill("#question", QUESTION);
  await page.press("#question", "Enter");
  await page.waitForSelector(".msg.bot .answer", { timeout: 60_000 });
  const answer = await page.textContent(".msg.bot .answer");
  expect(answer.includes("two working days"), `answer: ${answer}`);
  expect(await page.isVisible(".msg.bot details.trace"), "agent trace shown");
  step("question is answered with a citation");

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
  await page.click("#files-table button.quiet");
  await page.waitForSelector("#files-table", { state: "detached" });
  step("removing a file empties the collection");

  await page.click("#delete-collection");
  await page.waitForSelector("#welcome");
  expect((await page.textContent("#collection-list")).includes("None yet"), "collection gone");
  step("deleting the collection returns to the welcome screen");

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

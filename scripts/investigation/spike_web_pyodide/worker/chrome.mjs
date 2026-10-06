// Spike: open the worker page in the installed Chrome and print what it measured.
//
// Start `serve.py` first.
//
// Run:  node worker/chrome.mjs [--url http://localhost:8770/]

import { parseArgs } from "node:util";
import { chromium } from "playwright-core";

const { values: args } = parseArgs({ options: { url: { type: "string", default: "http://localhost:8770/" } } });

const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage();
  page.on("pageerror", (error) => console.error("page error:", error.message));
  page.on("console", (message) => {
    if (message.type() === "error") console.error("console error:", message.text());
  });
  await page.goto(args.url);
  await page.waitForFunction(() => window.RESULTS !== undefined, null, { timeout: 180_000 });
  console.log(JSON.stringify(await page.evaluate(() => window.RESULTS), null, 2));
} finally {
  await browser.close();
}

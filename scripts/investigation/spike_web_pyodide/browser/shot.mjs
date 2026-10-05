// Open a page served by `python -m nuiitivet.web run` in the installed Chrome and save a screenshot.
//
// Run:  node browser/shot.mjs --out shot.png [--url http://localhost:8000/] [--scale 2] [--width 900] [--height 700]

import { parseArgs } from "node:util";
import { chromium } from "playwright-core";

const { values: args } = parseArgs({
  options: {
    url: { type: "string", default: "http://localhost:8000/" },
    out: { type: "string" },
    scale: { type: "string", default: "1" },
    width: { type: "string", default: "900" },
    height: { type: "string", default: "700" },
  },
});

const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: Number(args.width), height: Number(args.height) },
    deviceScaleFactor: Number(args.scale),
  });
  page.on("pageerror", (error) => console.error("page error:", error.message));
  page.on("console", (message) => console.log(`[${message.type()}]`, message.text()));
  await page.goto(args.url);
  // The page removes the status element once the app runs.
  await page.waitForFunction(() => document.body.dataset.state !== undefined, null, { timeout: 180_000 });
  await page.waitForTimeout(1500);
  const status = await page.evaluate(() => document.getElementById("status")?.textContent ?? null);
  if (status !== null) console.error("status:", status);
  if (args.out) await page.screenshot({ path: args.out });
} finally {
  await browser.close();
}

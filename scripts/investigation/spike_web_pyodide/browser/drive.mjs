// Open a page served by `python -m nuiitivet.web run` in the installed Chrome, replay input, and save screenshots.
//
// Steps are `click:x,y`, `wheel:x,y,deltaY`, `key:Name`, `move:x,y`, `resize:w,h` and `wait:ms`.
// A screenshot `<out>-<n>.png` is saved before the first step and after each one.
//
// Run:  node browser/drive.mjs --out shots/run [--url http://localhost:8000/] [--scale 2] click:60,70 key:Tab

import { parseArgs } from "node:util";
import { chromium } from "playwright-core";

const { values: args, positionals: steps } = parseArgs({
  allowPositionals: true,
  options: {
    url: { type: "string", default: "http://localhost:8000/" },
    out: { type: "string" },
    scale: { type: "string", default: "1" },
  },
});

const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 900, height: 700 }, deviceScaleFactor: Number(args.scale) });
  page.on("pageerror", (error) => console.error("page error:", error.message));
  page.on("console", (message) => {
    if (!message.text().includes("404 (Not Found)")) console.log(`[${message.type()}]`, message.text());
  });
  await page.goto(args.url);
  await page.waitForFunction(() => document.getElementById("status")?.textContent !== "Loading…", null, {
    timeout: 180_000,
  });
  const status = await page.evaluate(() => document.getElementById("status")?.textContent ?? null);
  if (status !== null) console.error("status:", status);

  let shot = 0;
  const snap = async () => {
    await page.waitForTimeout(700);
    if (args.out) await page.screenshot({ path: `${args.out}-${shot++}.png` });
  };
  await snap();
  for (const step of steps) {
    const [kind, rest = ""] = step.split(":");
    const values = rest.split(",");
    if (kind === "click") await page.mouse.click(Number(values[0]), Number(values[1]));
    else if (kind === "move") await page.mouse.move(Number(values[0]), Number(values[1]));
    else if (kind === "wheel") {
      await page.mouse.move(Number(values[0]), Number(values[1]));
      await page.mouse.wheel(0, Number(values[2]));
    } else if (kind === "key") await page.keyboard.press(rest);
    else if (kind === "resize") await page.setViewportSize({ width: Number(values[0]), height: Number(values[1]) });
    else if (kind === "wait") await page.waitForTimeout(Number(rest));
    else throw new Error(`unknown step: ${step}`);
    await snap();
  }
} finally {
  await browser.close();
}

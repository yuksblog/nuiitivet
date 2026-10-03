// Spike: open the benchmark page in the installed Chrome and print what it measured.
//
// Start `serve.mjs` first. Headless Chrome may rasterize in software; the
// output names the renderer it used. For Safari and Firefox, and for a number
// on the real GPU, open the page in the browser by hand.
//
// Run:  node browser/chrome.mjs [--url http://localhost:8765/] [--headed]

import { parseArgs } from "node:util";
import { chromium } from "playwright-core";

const { values: args } = parseArgs({
  options: {
    url: { type: "string", default: "http://localhost:8765/" },
    headed: { type: "boolean", default: false },
  },
});

const browser = await chromium.launch({ channel: "chrome", headless: !args.headed });
try {
  const page = await browser.newPage({ viewport: { width: 1000, height: 1000 } });
  page.on("pageerror", (error) => console.error("page error:", error.message));
  await page.goto(args.url);
  await page.waitForFunction(() => window.RESULTS !== undefined, null, { timeout: 180_000 });
  console.log(JSON.stringify(await page.evaluate(() => window.RESULTS), null, 2));
} finally {
  await browser.close();
}

// Spike: open the benchmark page in a browser and print what it measured.
//
// Start `serve.mjs` first. Headless browsers may rasterize in software; the
// output names the renderer it used. `--browser firefox` uses Playwright's own
// Firefox build (`npx playwright install firefox`), not the release channel.
// `--pref name=value` sets a Firefox pref for the run; a value that parses as
// JSON (true, 0) is passed as that type.
//
// Run:  node browser/chrome.mjs [--url http://localhost:8765/] [--headed]
//                               [--browser chrome|firefox] [--pref webgl.out-of-process=false]

import { parseArgs } from "node:util";
import { chromium, firefox } from "playwright-core";

const { values: args } = parseArgs({
  options: {
    url: { type: "string", default: "http://localhost:8765/" },
    headed: { type: "boolean", default: false },
    browser: { type: "string", default: "chrome" },
    pref: { type: "string", multiple: true, default: [] },
  },
});

const firefoxUserPrefs = Object.fromEntries(
  args.pref.map((item) => {
    const [name, raw = ""] = item.split("=", 2);
    let value;
    try { value = JSON.parse(raw); } catch { value = raw; }
    return [name, value];
  }),
);

const browser = args.browser === "firefox"
  ? await firefox.launch({ headless: !args.headed, firefoxUserPrefs })
  : await chromium.launch({ channel: "chrome", headless: !args.headed });
try {
  const page = await browser.newPage({ viewport: { width: 1000, height: 1000 } });
  page.on("pageerror", (error) => console.error("page error:", error.message));
  await page.goto(args.url);
  await page.waitForFunction(() => window.RESULTS !== undefined, null, { timeout: 180_000 });
  console.log(JSON.stringify(await page.evaluate(() => window.RESULTS), null, 2));
} finally {
  await browser.close();
}

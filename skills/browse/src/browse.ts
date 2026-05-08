#!/usr/bin/env bun
import { chromium, type BrowserContext, type Page } from "playwright";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { resolve } from "node:path";
import TurndownService from "turndown";

const PROFILE_DIR = resolve(homedir(), ".zbt-browse/profile");
const STATE_FILE = resolve(homedir(), ".zbt-browse/last-url");

const HELP = `zbt-browse — fetch web content via headless Chromium

Usage:
  browse goto <url>           Navigate to URL (waits for networkidle)
  browse text [url]           Print page innerText (loads url if given)
  browse html [url]           Print page outerHTML
  browse markdown [url]       Print page as markdown (article-friendly)
  browse screenshot <path>    Save full-page PNG to path
  browse url                  Print current page URL
  browse clear                Wipe profile (cookies, cache)

Notes:
  - Persistent profile at ~/.zbt-browse/profile (cookies survive between calls)
  - No daemon — each invocation is a fresh subprocess (~2-4s).
  - Last visited URL cached at ~/.zbt-browse/last-url so 'text' / 'html' / 'markdown'
    without an arg re-loads the last URL.
`;

function ensureDirs() {
  const parent = resolve(PROFILE_DIR, "..");
  if (!existsSync(parent)) mkdirSync(parent, { recursive: true });
  if (!existsSync(PROFILE_DIR)) mkdirSync(PROFILE_DIR, { recursive: true });
}

async function withContext<T>(fn: (ctx: BrowserContext, page: Page) => Promise<T>): Promise<T> {
  ensureDirs();
  const ctx = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: true,
    viewport: { width: 1280, height: 800 },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    locale: "en-US",
    timezoneId: "America/New_York",
    args: [
      "--disable-blink-features=AutomationControlled",
      "--disable-features=IsolateOrigins,site-per-process",
    ],
  });
  // Soft anti-fingerprint nudge: hide webdriver flag
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
  });
  const page = ctx.pages()[0] ?? (await ctx.newPage());
  try {
    return await fn(ctx, page);
  } finally {
    await ctx.close();
  }
}

async function loadUrl(page: Page, url: string) {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
  // Soft post-load wait: many sites finish JS hydration after domcontentloaded.
  // Cloudflare interstitials usually clear within ~5s.
  try {
    await page.waitForLoadState("networkidle", { timeout: 10_000 });
  } catch {
    // Fine — some pages never go fully idle (analytics, polling).
  }
  writeFileSync(STATE_FILE, page.url());
}

function lastUrl(): string | null {
  if (!existsSync(STATE_FILE)) return null;
  return Bun.file(STATE_FILE).text() as unknown as string;
}

async function cmdGoto(url: string) {
  await withContext(async (_ctx, page) => {
    await loadUrl(page, url);
    console.log(page.url());
  });
}

async function cmdText(url?: string) {
  await withContext(async (_ctx, page) => {
    const target = url ?? (await lastUrl());
    if (!target) throw new Error("No URL provided and no cached last URL.");
    await loadUrl(page, target);
    const text = await page.evaluate(() => document.body?.innerText ?? "");
    console.log(text);
  });
}

async function cmdHtml(url?: string) {
  await withContext(async (_ctx, page) => {
    const target = url ?? (await lastUrl());
    if (!target) throw new Error("No URL provided and no cached last URL.");
    await loadUrl(page, target);
    console.log(await page.content());
  });
}

async function cmdMarkdown(url?: string) {
  await withContext(async (_ctx, page) => {
    const target = url ?? (await lastUrl());
    if (!target) throw new Error("No URL provided and no cached last URL.");
    await loadUrl(page, target);
    const html = await page.evaluate(() => {
      // Prefer <article> / <main> if present, else fall back to <body>.
      const root =
        document.querySelector("article") ??
        document.querySelector("main") ??
        document.body;
      return root?.innerHTML ?? "";
    });
    const td = new TurndownService({ headingStyle: "atx", codeBlockStyle: "fenced" });
    console.log(td.turndown(html));
  });
}

async function cmdScreenshot(path: string) {
  await withContext(async (_ctx, page) => {
    const target = await lastUrl();
    if (!target) throw new Error("No cached URL. Run goto <url> first.");
    await loadUrl(page, target);
    await page.screenshot({ path, fullPage: true });
    console.log(path);
  });
}

async function cmdUrl() {
  const u = await lastUrl();
  if (!u) throw new Error("No cached URL.");
  console.log(u.trim());
}

async function cmdClear() {
  const { rmSync } = await import("node:fs");
  if (existsSync(PROFILE_DIR)) rmSync(PROFILE_DIR, { recursive: true, force: true });
  if (existsSync(STATE_FILE)) rmSync(STATE_FILE);
  console.log("cleared");
}

const [cmd, ...rest] = process.argv.slice(2);

try {
  switch (cmd) {
    case "goto":
      if (!rest[0]) throw new Error("goto requires a URL");
      await cmdGoto(rest[0]);
      break;
    case "text":
      await cmdText(rest[0]);
      break;
    case "html":
      await cmdHtml(rest[0]);
      break;
    case "markdown":
      await cmdMarkdown(rest[0]);
      break;
    case "screenshot":
      if (!rest[0]) throw new Error("screenshot requires a path");
      await cmdScreenshot(rest[0]);
      break;
    case "url":
      await cmdUrl();
      break;
    case "clear":
      await cmdClear();
      break;
    case "help":
    case "--help":
    case "-h":
    case undefined:
      console.log(HELP);
      break;
    default:
      console.error(`Unknown command: ${cmd}\n`);
      console.error(HELP);
      process.exit(2);
  }
} catch (e: any) {
  console.error(`error: ${e?.message ?? e}`);
  process.exit(1);
}

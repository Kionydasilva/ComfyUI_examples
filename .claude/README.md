# Claude Code setup

## Browser automation

The `dev-browser` skill lives in `.agents/skills/dev-browser` (installed via
`npx skills add`, pinned in `skills-lock.json`).

Its documented setup — `npm install -g dev-browser && dev-browser install` —
only half works in Claude Code on the web. The install step downloads Chrome
for Testing from `cdn.playwright.dev`, and the environment's network allowlist
answers 403, so no browser ever lands on disk.

`.claude/hooks/session-start.sh` works around this on every session start:

- installs the `dev-browser` CLI,
- runs `dev-browser install` for its daemon dependencies and swallows the
  expected download failure,
- puts `.claude/scripts/dev-browser-here` on `PATH`.

Use the wrapper instead of `dev-browser` directly. It attaches over CDP to the
Chromium already bundled in the image, starting it on first use:

```bash
dev-browser-here <<'EOF'
  const page = await browser.getPage("main");
  await page.goto("http://127.0.0.1:8188/");
  await saveScreenshot(await page.screenshot(), "comfy.png");
EOF
```

Local addresses connect directly; everything else goes through the agent proxy,
so reachable sites are limited to the environment's network policy. Screenshots
land in `~/.dev-browser/tmp/`.

The hook is a no-op outside the remote container — local machines keep their own
setup.

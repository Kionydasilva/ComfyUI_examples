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

## Video

The `watch` skill lives in `.agents/skills/watch` (installed via `npx skills
add bradautomates/claude-video`, pinned in `skills-lock.json`), with the usual
symlink from `.claude/skills/watch`. It hands Claude frames plus a transcript
for a video URL or a local file.

Unlike `dev-browser`, this one is **not** bootstrapped on session start. In the
remote container its two headline paths are closed by the network policy:

- `yt-dlp` against YouTube (and every other remote host it supports) gets a
  403 on CONNECT from the agent proxy, so URLs do not resolve.
- `api.groq.com` and `api.openai.com` are unreachable too, so the Whisper
  fallback cannot run and videos without native captions come back frames-only.

What does work remotely is a **local video file, frames only**. `ffmpeg` is
absent from the image, so install it first:

```bash
apt-get update && apt-get install -y ffmpeg
python3 .agents/skills/watch/scripts/watch.py clip.mp4 --no-whisper
```

`watch.py` itself does not need `yt-dlp` on a local path — only `setup.py`'s
preflight insists on it, and that check is advisory. `pip install yt-dlp`
silences it.

That costs ~90s, which is why it is not in `.claude/hooks/session-start.sh` —
paying it on every session start to service the one path that still works is a
bad trade. The skill's own `setup.py --json` preflight detects the missing
binaries and prints the same commands.

On a local machine the skill works as documented upstream: URLs, captions, and
the Whisper fallback all reachable.

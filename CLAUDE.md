# ComfyUI_examples

Official ComfyUI example workflows. Documentation repo — no build, no tests, no
dependencies to install.

## Network policy (verified 2026-09-15, remote container)

Outbound goes through an agent proxy on a narrow allowlist. Do not re-derive
this; do not retry a blocked host.

| Host | Result |
|------|--------|
| `github.com`, `raw.githubusercontent.com` | reachable |
| `pypi.org`, `registry.npmjs.org` | reachable (in `noProxy`) |
| `huggingface.co`, `civitai.com` | **403 on CONNECT** |
| `youtube.com`, `google.com`, `instagram.com` | **403 on CONNECT** |
| `api.groq.com`, `api.openai.com` | **403 on CONNECT** |

Consequences: no model or LoRA downloads here. No watching videos from a URL.
The block is at the proxy, so every tool hits it — `yt-dlp`, `curl`, `WebFetch`
and headless Chromium all fail identically. Confirm with
`curl -sS "$HTTPS_PROXY/__agentproxy/status"`.

## Skills

- `dev-browser` — headless Chromium over CDP. Bootstrapped by
  `.claude/hooks/session-start.sh`. Use `.claude/scripts/dev-browser-here`.
- `watch` — video → frames + transcript. Local files only here (see above).
  Needs `apt-get install -y ffmpeg`, which is **not** installed on session start.

Both live in `.agents/skills/`, symlinked from `.claude/skills/`, pinned in
`skills-lock.json`. See `.claude/README.md` for why neither is fully automated.

## WAN 2.2 workflows

`wan22_max_quality/wan22_{i2v,t2v}_max_quality.json` are hand-built from core
nodes only, so they import without any custom-node install. 1280x720, 81 frames,
16 fps, MoE split across two chained `KSamplerAdvanced` passes. The lightx2v
distill LoRAs are wired but bypassed — quality path by default, Ctrl+B to
switch. Needs ~24GB VRAM; use `wan22/*_5B.json` below that.

`wan22_max_quality/tools/` holds the validators used to build them.

The upstream `wan22/*.json` files shipped with the repo are the official
reference — prefer them as a starting point over reconstructing a workflow from
a video or a screenshot.

## Conventions

Workflow JSON is paired with a `.webp` preview of the same name. Keep that
pairing when adding examples.

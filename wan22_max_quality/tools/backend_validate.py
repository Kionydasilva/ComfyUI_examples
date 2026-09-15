#!/usr/bin/env python3
"""Convert litegraph workflows to API format and run ComfyUI's real validator.

This is the end-to-end check: execution.validate_prompt() is the same function
the backend runs when you press Queue Prompt, so anything it accepts here will
be accepted by a real ComfyUI.
"""
import asyncio
import json
import sys

OUT_PATHS = sys.argv[1:]
sys.argv = [sys.argv[0], "--cpu"]

import comfy.options  # noqa: E402
comfy.options.enable_args_parsing()

import nodes  # noqa: E402
import execution  # noqa: E402
from comfy_api.internal import _ComfyNodeInternal  # noqa: E402

PRIMITIVE = {"INT", "FLOAT", "STRING", "BOOLEAN"}
MUTED, BYPASSED = 2, 4


def input_spec(cls):
    if issubclass(cls, _ComfyNodeInternal):
        return cls.GET_NODE_INFO_V1()["input"]
    return cls.INPUT_TYPES()


# Live INPUT_TYPES() uses tuples; the JSON object_info form uses lists.
SEQ = (list, tuple)


def spec_type(spec):
    """Input type as a string. Combos (legacy sequence, COMBO, DynamicCombo
    dict) all collapse to "COMBO" because they all render as widgets."""
    t = spec[0] if isinstance(spec, SEQ) and spec else spec
    return t if isinstance(t, str) else "COMBO"


def spec_opts(spec):
    if isinstance(spec, SEQ) and len(spec) > 1 and isinstance(spec[1], dict):
        return spec[1]
    return {}


def widget_names(cls):
    """Widget slots in UI order, including synthetic control_after_generate."""
    out = []
    inp = input_spec(cls)
    for section in ("required", "optional"):
        for name, spec in (inp.get(section) or {}).items():
            t = spec_type(spec)
            if t != "COMBO" and t not in PRIMITIVE:
                continue
            out.append(name)
            if spec_opts(spec).get("control_after_generate"):
                out.append(None)          # synthetic, no API counterpart
    return out


def socket_names(cls):
    out = []
    inp = input_spec(cls)
    for section in ("required", "optional"):
        for name, spec in (inp.get(section) or {}).items():
            t = spec_type(spec)
            if t == "COMBO" or t in PRIMITIVE:
                continue
            out.append(name)
    return out


def to_api(wf):
    nodes_by_id = {n["id"]: n for n in wf["nodes"]}
    links = {l[0]: l for l in wf["links"]}

    def resolve(link_id, depth=0):
        """Follow a link back past bypassed nodes to a live producer."""
        if link_id is None or depth > 64:
            return None
        _, src, sslot, _, _, ltype = links[link_id]
        src_node = nodes_by_id[src]
        if src_node["mode"] != BYPASSED:
            return [str(src), sslot]
        # Bypass: forward to this node's first input of the same type.
        for inp in src_node.get("inputs") or []:
            if inp["type"] == ltype:
                return resolve(inp.get("link"), depth + 1)
        return None

    prompt = {}
    for n in wf["nodes"]:
        if n["type"] == "Note" or n["mode"] in (MUTED, BYPASSED):
            continue
        cls = nodes.NODE_CLASS_MAPPINGS[n["type"]]
        entry = {"class_type": n["type"], "inputs": {},
                 "_meta": {"title": n.get("title", n["type"])}}

        wv = n.get("widgets_values") or []
        promoted = {i["name"] for i in (n.get("inputs") or [])}
        slots = [w for w in widget_names(cls) if w not in promoted]
        for name, value in zip(slots, wv):
            if name is not None:
                entry["inputs"][name] = value

        for inp in n.get("inputs") or []:
            ref = resolve(inp.get("link"))
            if ref is not None:
                entry["inputs"][inp["name"]] = ref
        prompt[str(n["id"])] = entry
    return prompt


async def main():
    await nodes.init_extra_nodes(init_custom_nodes=False, init_api_nodes=False)
    failed = 0
    for path in OUT_PATHS:
        with open(path, encoding="utf-8") as f:
            wf = json.load(f)
        prompt = to_api(wf)
        name = path.split("/")[-1]
        result = await execution.validate_prompt(f"val-{name}", prompt, None)
        valid = result[0]
        print(f"\n{'PASS' if valid else 'FAIL'} {name}  "
              f"({len(prompt)} nodes queued, outputs={result[2]})")
        if not valid:
            failed += 1
            print("  error:", json.dumps(result[1], indent=2)[:1500])
        for node_id, err in (result[3] or {}).items():
            print(f"  node {node_id}: "
                  f"{[e.get('message') for e in err.get('errors', [])]}")
    print("\n" + ("BACKEND VALIDATION PASSED" if not failed
                  else f"{failed} WORKFLOWS REJECTED"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

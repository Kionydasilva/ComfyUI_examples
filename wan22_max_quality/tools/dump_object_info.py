#!/usr/bin/env python3
"""Dump ComfyUI's live object_info to JSON.

Mirrors server.py:node_info() so the validator sees exactly the node schemas
the real backend would enforce. Run from inside the ComfyUI checkout.
"""
import asyncio
import json
import os
import sys

OUT = sys.argv[1]
sys.argv = [sys.argv[0], "--cpu"]  # comfy reads cli_args at import time

import comfy.options
comfy.options.enable_args_parsing()

import nodes
from comfy_api.internal import _ComfyNodeInternal


def node_info(name):
    cls = nodes.NODE_CLASS_MAPPINGS[name]
    if issubclass(cls, _ComfyNodeInternal):
        return cls.GET_NODE_INFO_V1()
    info = {
        "input": cls.INPUT_TYPES(),
        "output": list(cls.RETURN_TYPES),
        "output_name": list(getattr(cls, "RETURN_NAMES", cls.RETURN_TYPES)),
        "name": name,
        "category": getattr(cls, "CATEGORY", "sd"),
        "output_node": bool(getattr(cls, "OUTPUT_NODE", False)),
    }
    return info


async def main():
    await nodes.init_extra_nodes(init_custom_nodes=False, init_api_nodes=False)
    out, failed = {}, []
    for name in nodes.NODE_CLASS_MAPPINGS:
        try:
            out[name] = json.loads(json.dumps(node_info(name), default=str))
        except Exception as exc:  # nodes with unserializable defaults
            failed.append(f"{name}: {exc}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"dumped {len(out)} node types, {len(failed)} skipped")
    for f_ in failed[:10]:
        print("  skipped:", f_)


if __name__ == "__main__":
    asyncio.run(main())

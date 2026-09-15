#!/usr/bin/env python3
"""Validate a ComfyUI litegraph workflow JSON.

Two independent sources of truth:
  1. object_info.json  - dumped from a real ComfyUI install (node existence,
     socket names/types, widget schemas, combo option lists).
  2. reference workflows shipped by ComfyUI itself - empirical widget counts
     per node type, which catches UI-only widgets (control_after_generate,
     the LoadImage upload button) that object_info does not describe.

Exit code 0 = clean, 1 = errors found.
"""
import json
import sys
import glob
import os

# Socket types carry data between nodes; everything else renders as a widget.
PRIMITIVE = {"INT", "FLOAT", "STRING", "BOOLEAN"}


def load_object_info(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _spec_type(spec):
    """Input type as a plain string; legacy combos come back as 'COMBO'."""
    t = spec[0] if isinstance(spec, list) and spec else spec
    return "COMBO" if isinstance(t, list) else t


def _spec_opts(spec):
    return spec[1] if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict) else {}


def _spec_options(spec):
    """Allowed values of a combo input, whichever serialization it uses."""
    t = spec[0] if isinstance(spec, list) and spec else spec
    if isinstance(t, list):
        return t                          # legacy: [["a", "b"]]
    if t == "COMBO":
        return _spec_opts(spec).get("options") or []
    return None


def _ordered_inputs(info):
    inp = info.get("input", {})
    for section in ("required", "optional"):
        for name, spec in (inp.get(section) or {}).items():
            yield section, name, spec


def schema_sockets(info):
    """Ordered (name, type) of inputs that render as sockets, not widgets."""
    out = []
    for _, name, spec in _ordered_inputs(info):
        t = _spec_type(spec)
        if t == "COMBO" or t in PRIMITIVE:
            continue
        out.append((name, t))
    return out


def schema_widgets(info):
    """Ordered widget names, including synthetic control_after_generate."""
    out = []
    for _, name, spec in _ordered_inputs(info):
        t = _spec_type(spec)
        if t != "COMBO" and t not in PRIMITIVE:
            continue
        out.append(name)
        if _spec_opts(spec).get("control_after_generate"):
            out.append(name + "_control")
    return out


def schema_combos(info):
    """name -> allowed option list, for every combo input."""
    combos = {}
    for _, name, spec in _ordered_inputs(info):
        opts = _spec_options(spec)
        if opts is not None:
            combos[name] = opts
    return combos


def reference_widget_counts(paths):
    """node type -> set of widget-list lengths seen in official workflows."""
    counts = {}
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        if not isinstance(d, dict) or "nodes" not in d:
            continue
        for n in d["nodes"]:
            w = n.get("widgets_values")
            if isinstance(w, list):
                counts.setdefault(n["type"], set()).add(len(w))
    return counts


def validate(wf_path, oinfo, refcounts):
    errors, warnings = [], []
    with open(wf_path, encoding="utf-8") as f:
        wf = json.load(f)

    nodes = wf["nodes"]
    by_id = {n["id"]: n for n in nodes}
    if len(by_id) != len(nodes):
        errors.append("duplicate node ids")

    # --- node types exist -------------------------------------------------
    for n in nodes:
        if n["type"] == "Note":
            continue
        if n["type"] not in oinfo:
            errors.append(f"node {n['id']}: unknown node type {n['type']!r}")

    # --- socket inputs/outputs match the real schema ----------------------
    for n in nodes:
        info = oinfo.get(n["type"])
        if not info:
            continue
        want = schema_sockets(info)
        got = [(i["name"], i["type"]) for i in n.get("inputs", []) or []]
        want_names = [w[0] for w in want]
        got_names = [g[0] for g in got]
        # A widget can be promoted to a socket in the UI ("convert widget to
        # input"), so trailing extras are legal as long as they name widgets.
        widget_names = set(schema_widgets(info))
        promoted = [g for g in got_names if g in widget_names]
        plain = [g for g in got_names if g not in widget_names]
        if plain != want_names:
            errors.append(
                f"node {n['id']} ({n['type']}): input sockets {got_names} "
                f"!= schema {want_names}")
        unknown = [g for g in got_names
                   if g not in widget_names and g not in want_names]
        if unknown:
            errors.append(
                f"node {n['id']} ({n['type']}): inputs not in schema: {unknown}")
        schema_types = dict(want)
        for gn, gt in got:
            if gn in schema_types and gt != schema_types[gn]:
                errors.append(
                    f"node {n['id']} ({n['type']}): input {gn!r} type "
                    f"{gt!r} != schema {schema_types[gn]!r}")
        n["_promoted"] = len(promoted)

        want_out = list(zip(info.get("output_name", []), info.get("output", [])))
        got_out = [(o["name"], o["type"]) for o in n.get("outputs", []) or []]
        if got_out and [g[1] for g in got_out] != [w[1] for w in want_out]:
            errors.append(
                f"node {n['id']} ({n['type']}): output types "
                f"{[g[1] for g in got_out]} != schema {[w[1] for w in want_out]}")

    # --- required inputs are connected ------------------------------------
    for n in nodes:
        info = oinfo.get(n["type"])
        if not info:
            continue
        required = set((info.get("input", {}).get("required") or {}).keys())
        for i in n.get("inputs", []) or []:
            if i["name"] in required and i.get("link") is None:
                errors.append(
                    f"node {n['id']} ({n['type']}): required input "
                    f"{i['name']!r} is not connected")

    # --- combo widget values are legal ------------------------------------
    # Combos populated from the user's model folders cannot be checked here:
    # this machine has no models installed, so their option list is empty.
    DISK_COMBOS = ("image", "video", "audio")
    for n in nodes:
        info = oinfo.get(n["type"])
        if not info:
            continue
        wv = n.get("widgets_values") or []
        names = schema_widgets(info)
        for name, options in schema_combos(info).items():
            if name.endswith("_name") or name in DISK_COMBOS or not options:
                continue
            if name not in names:
                continue
            idx = names.index(name)
            if idx >= len(wv):
                errors.append(
                    f"node {n['id']} ({n['type']}): missing widget value for "
                    f"{name!r}")
            elif wv[idx] not in options:
                errors.append(
                    f"node {n['id']} ({n['type']}): {name}={wv[idx]!r} is not "
                    f"one of {options[:8]}{'...' if len(options) > 8 else ''}")

    # --- widget count: schema-derived, cross-checked against official -----
    for n in nodes:
        wv = n.get("widgets_values")
        if not isinstance(wv, list):
            continue
        info = oinfo.get(n["type"])
        seen = refcounts.get(n["type"])
        expect = (len(schema_widgets(info)) - n.get("_promoted", 0)) \
            if info else None
        if expect is not None and seen and expect not in seen:
            # Node has UI-only widgets (upload buttons etc.) that the backend
            # schema does not describe; trust the official workflows instead.
            expect = None
        if expect is not None and len(wv) != expect:
            errors.append(
                f"node {n['id']} ({n['type']}): {len(wv)} widget values, "
                f"schema expects {expect} ({schema_widgets(info)})")
        elif expect is None and seen and len(wv) not in seen:
            errors.append(
                f"node {n['id']} ({n['type']}): {len(wv)} widget values, "
                f"official workflows use {sorted(seen)}")

    # --- link table integrity ---------------------------------------------
    link_ids = [l[0] for l in wf["links"]]
    if len(set(link_ids)) != len(link_ids):
        errors.append("duplicate link ids")
    links = {l[0]: l for l in wf["links"]}

    for lid, src, sslot, dst, dslot, ltype in wf["links"]:
        if src not in by_id:
            errors.append(f"link {lid}: origin node {src} missing")
            continue
        if dst not in by_id:
            errors.append(f"link {lid}: target node {dst} missing")
            continue
        s, d = by_id[src], by_id[dst]
        souts = s.get("outputs") or []
        dins = d.get("inputs") or []
        if sslot >= len(souts):
            errors.append(f"link {lid}: origin slot {sslot} out of range")
            continue
        if dslot >= len(dins):
            errors.append(f"link {lid}: target slot {dslot} out of range")
            continue
        if souts[sslot]["type"] != dins[dslot]["type"]:
            errors.append(
                f"link {lid}: type mismatch {souts[sslot]['type']} -> "
                f"{dins[dslot]['type']}")
        if ltype != souts[sslot]["type"]:
            errors.append(f"link {lid}: declared type {ltype!r} != origin type")
        if lid not in (souts[sslot].get("links") or []):
            errors.append(f"link {lid}: not listed on origin node {src} output")
        if dins[dslot].get("link") != lid:
            errors.append(f"link {lid}: target node {dst} input does not point back")

    # every link referenced by a node must exist in the link table
    for n in nodes:
        for i in n.get("inputs", []) or []:
            if i.get("link") is not None and i["link"] not in links:
                errors.append(
                    f"node {n['id']}: input {i['name']!r} references "
                    f"missing link {i['link']}")
        for o in n.get("outputs", []) or []:
            for lid in o.get("links") or []:
                if lid not in links:
                    errors.append(
                        f"node {n['id']}: output {o['name']!r} references "
                        f"missing link {lid}")

    # --- counters ---------------------------------------------------------
    if wf["last_node_id"] < max(by_id):
        errors.append("last_node_id lower than highest node id")
    if link_ids and wf["last_link_id"] < max(link_ids):
        errors.append("last_link_id lower than highest link id")

    # --- execution order is topological -----------------------------------
    order = {n["id"]: n["order"] for n in nodes}
    for lid, src, _, dst, _, _ in wf["links"]:
        if src in order and dst in order and order[src] >= order[dst]:
            errors.append(
                f"link {lid}: node {src} (order {order[src]}) runs after "
                f"target {dst} (order {order[dst]})")

    # --- output node present ----------------------------------------------
    if not any(oinfo.get(n["type"], {}).get("output_node") for n in nodes):
        errors.append("workflow has no output node")

    # --- reachability: output node must trace back to a loader ------------
    incoming = {}
    for _, src, _, dst, _, _ in wf["links"]:
        incoming.setdefault(dst, []).append(src)
    outs = [n["id"] for n in nodes
            if oinfo.get(n["type"], {}).get("output_node")]
    seen, stack = set(), list(outs)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(incoming.get(cur, []))
    dangling = [n["id"] for n in nodes
                if n["type"] != "Note" and n["id"] not in seen]
    if dangling:
        warnings.append(f"nodes not feeding any output: {dangling}")

    return errors, warnings


def main():
    oinfo = load_object_info(sys.argv[1])
    refs = sorted(glob.glob(os.path.join(sys.argv[2], "*", "*.json")))
    refcounts = reference_widget_counts(refs)
    print(f"object_info: {len(oinfo)} node types | "
          f"reference workflows: {len(refs)}")

    total = 0
    for wf_path in sys.argv[3:]:
        errors, warnings = validate(wf_path, oinfo, refcounts)
        name = os.path.basename(wf_path)
        if errors:
            print(f"\nFAIL {name}")
            for e in errors:
                print("  ERROR  ", e)
        else:
            print(f"\nPASS {name}")
        for w in warnings:
            print("  warn   ", w)
        total += len(errors)
    print("\n" + ("ALL WORKFLOWS VALID" if total == 0 else f"{total} ERRORS"))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())

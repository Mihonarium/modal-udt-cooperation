"""Side-by-side: greedy modal UDT, V3-B, V4, FairBot, PrudentBot (deterministic evaluator) and V5 (randomised)
on the named games.  Writes compare.json for the report."""
import json
from modal import *; from v3 import V3; from v4 import V4
from run import G, analysis
from rmodal import *; from v5 import V5, fair_point
from run_v5 import NAMED, RND, fmt

out = {}
for g in NAMED:
    an = analysis(g); pr, pc, uv, desc = fair_point(g, RND.npub)
    tgt = (0, 0) if g.name.startswith("PD") else an["target"]
    ctx = Ctx(g, tgt, an["maxmin_act"])
    old = {"UDT": lambda: ModalUDT("UDT", default=lambda gg, r: an["maxmin_act"][r]),
           "V3-B": lambda: V3("V3-B", order="exploit-last"), "V4": lambda: V4("V4"),
           "FB": lambda: FairBot(), "PB": lambda: PrudentBot()}
    rows = {}
    for name, mk in old.items():
        X = mk(); cells = {}
        def cell(A, B, seat):
            r, c, s = play(g, A, B, ctx, N=120)
            return dict(play=f"{g.acts[0][r]},{g.acts[1][c]}", ev=list(g.U[(r, c)]))
        cells["copy"] = cell(X, mk(), 0)
        cells["FB"] = cell(X, FairBot(), 0); cells["PB"] = cell(X, PrudentBot(), 0)
        for a in range(g.n(1)): cells[f"Const {g.acts[1][a]}"] = cell(X, Const(a), 0)
        rows[name] = cells
    rctx = RCtx(g, RND); V = V5(); cells = {}
    def rcell(B, seat=0):
        px, py, s, ev = rplay(g, V, B, rctx, N=60)
        return dict(play=f"[{fmt(dist(g, px, RND, 0), g.acts[0])}],[{fmt(dist(g, py, RND, 1), g.acts[1])}]", ev=list(ev))
    cells["copy"] = rcell(V5("V5'"))
    cells["FB"] = rcell(RFairBot((pr, pc), an["maxmin_act"], "FB-F")); cells["PB"] = rcell(RPrudentBot((pr, pc), an["maxmin_act"], "PB-F"))
    for a in range(g.n(1)): cells[f"Const {g.acts[1][a]}"] = rcell(RConst(a))
    rows["V5"] = cells
    out[g.name] = dict(acts=g.acts, U={f"{i},{j}": v for (i, j), v in g.U.items()}, fair=desc, fair_payoff=uv,
                       maxmin=an["maxmin_val"], rows=rows)
    print(g.name, desc, uv)
    for n, c in rows.items(): print("  ", n, {k: v["play"] for k, v in c.items()})
json.dump(out, open("compare.json", "w"), indent=1)

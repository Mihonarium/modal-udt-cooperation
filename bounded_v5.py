"""Bounded (runnable) V5: a real program that reads the opponent's source text and halts.

What is bounded here and how (see README "Bounded V5"):
  * Opponents are source strings in two recognised forms: a STONE (a fixed policy table over the draws,
    i.e. a commitment, pure or mixed) or a V5B spec line like this program's own.  Any other source is
    unknown: nothing is assumed about it and the bot plays its maxmin action.
  * Facts about a stone are read off its table.  Facts about a V5B opponent's play against a stone are
    obtained by RUNNING it against that stone (every such run halts: a stone runs nothing).
  * The one Löbian step, tier B between two V5B bots, is decided by the exact bounded proof search of
    bounded.py (the BPC calculus): the bot checks that neither side exploits the other and that both aim at
    the same fair point, and then the question "do we both play F" is FairBot_k vs FairBot_m, searched in
    BPC with the bots' own budgets.  Cooperation needs budget >= 1 on both sides (bounded_tables.txt).
  * Tier C (answering a commitment) is applied to stones only.  Against another V5B it is skipped: reading
    its policy against me would mean running it against me, which runs me against it, and so on.  Two V5B
    bots that aim at different fair points therefore end at their maxmin actions (the idealised V5 reaches
    a settlement there through stratified PA+k checks, which have no bounded counterpart here).
Draws: r_pub in range(npub) (public), r_f in range(m) (private, fine).  No coarse private draw.
"""
import re, json
from itertools import product
from rmodal import Game
from v5 import fair_point, maxmin_val
import bounded as B

def v5b(fair="nbs", budget=1, npub=2, m=4):
    return f"V5B fair={fair} budget={budget} npub={npub} m={m}"
def stone(table):
    """table[r_pub][r_f] = action name."""
    return "STONE " + json.dumps(table)
def const_stone(a, npub, m): return stone([[a] * m for _ in range(npub)])
def mix_stone(x, y, j, npub, m): return stone([[x if f < j else y for f in range(m)] for _ in range(npub)])

def parse(src):
    src = src.strip()
    if src.startswith("STONE "): return ("stone", json.loads(src[6:]))
    mm = re.fullmatch(r"V5B fair=(\w+) budget=(\d+) npub=(\d+) m=(\d+)", src)
    if mm: return ("v5b", dict(fair=mm[1], budget=int(mm[2]), npub=int(mm[3]), m=int(mm[4])))
    return ("unknown", None)

_fair = {}
def fair_of(g, spec):
    key = (g.name, spec["fair"], spec["npub"])
    if key not in _fair: _fair[key] = _fair_of(g, spec)
    return _fair[key]
def _fair_of(g, spec):
    if spec["fair"] == "nbs": return fair_point(g, spec["npub"])
    if spec["fair"].startswith("ult"):   # ult<o>: Ultimatum with "fair offer o" (for the different-fairness test)
        o = int(spec["fair"][3:]); n = g.n(0) - 1
        return (lambda p: o), (lambda p: o), (float(n - o), float(o)), f"offer {o}"
    raise ValueError(spec["fair"])

_pol = {}
def policy(g, X, Y, role):
    """The full policy table of program X in `role` against program Y: table[r_pub][r_f] = action index."""
    key = (g.name, X, Y, role)
    if key not in _pol: _pol[key] = _policy(g, X, Y, role)
    return _pol[key]
def _policy(g, X, Y, role):
    kind, spec = parse(X)
    if kind == "stone":
        return [[g.acts[role].index(a) for a in row] for row in spec]
    assert kind == "v5b", "unknown program cannot be run"
    return [[act(g, X, Y, role, (p, f)) for f in range(spec["m"])] for p in range(spec["npub"])]

_loeb = {}
def loeb(kx, ky):
    """FairBot_kx vs FairBot_ky in the exact bounded calculus of bounded.py: does the row bot cooperate?"""
    if (kx, ky) not in _loeb:
        _loeb[(kx, ky)] = B.act(B.PD, B.fairbot(kx), B.fairbot(ky), 0) == 0
    return _loeb[(kx, ky)]

def tier_a(g, spec, Y, role):
    """Tier A of a V5B bot with `spec` in `role` against program Y: the action it exploits with, or None."""
    nA, nB = g.n(role), g.n(1 - role)
    U = lambda a, b: g.u(role, a, b)
    _, _, uv, _ = fair_of(g, spec); uF = uv[role]
    cands = []
    for b in range(nB):
        a = max(range(nA), key=lambda x: (U(x, b), -x))
        if U(a, b) > uF: cands.append((U(a, b), a, b))
    for _, a, b in sorted(cands, key=lambda t: -t[0]):
        ky, _ = parse(Y)
        if ky == "unknown": continue
        tab = policy(g, Y, const_stone(g.acts[role][a], spec["npub"], spec["m"]), 1 - role)
        if all(v == b for row in tab for v in row): return a
    return None

def act(g, X, Y, role, draw):
    """Program X (a V5B source) in `role` against source Y, at X's draw (r_pub, r_f).  Returns an action index."""
    kind, spec = parse(X); assert kind == "v5b"
    p, f = draw; npub, m, k = spec["npub"], spec["m"], spec["budget"]
    nA, nB = g.n(role), g.n(1 - role)
    U = lambda a, b: g.u(role, a, b); V = lambda a, b: g.u(1 - role, b, a)
    pr, pc, uv, _ = fair_of(g, spec)
    myF, opF = (pr, pc) if role == 0 else (pc, pr); uF, vF = uv[role], uv[1 - role]
    ky, yspec = parse(Y)
    # A: exploit
    a = tier_a(g, spec, Y, role)
    if a is not None: return a
    # B: fair
    if ky == "stone":
        if all(v == g.acts[1 - role][opF(pp)] for pp, row in enumerate(yspec) for v in row): return myF(p)
    elif ky == "v5b":
        same_F = (yspec["npub"] == npub and fair_of(g, yspec)[2] == uv
                  and all(fair_of(g, yspec)[r](pp) == (pr, pc)[r](pp) for r in (0, 1) for pp in range(npub)))
        if same_F and tier_a(g, yspec, X, 1 - role) is None and loeb(k, yspec["budget"]): return myF(p)
    # C: answer a commitment (stones only)
    if ky == "stone":
        row = yspec[p]; q = [sum(g.acts[1 - role].index(v) == b for v in row) / len(row) for b in range(nB)]
        myev = lambda x: sum(q[b] * U(x, b) for b in range(nB)); opev = lambda x: sum(q[b] * V(x, b) for b in range(nB))
        a_star = max(range(nA), key=lambda x: (myev(x), x == myF(p), -x)); v_give = opev(a_star)
        a_ref = min(range(nA), key=lambda x: (opev(x), -myev(x), x != myF(p), x)); v_ref = opev(a_ref)
        if v_give <= vF: return a_star
        if v_ref >= vF: return a_ref
        thr = (vF - v_ref) / (v_give - v_ref)
        pm = max(i for i in range(m + 1) if i / m < thr)
        return a_star if f < pm else a_ref
    # D: maxmin
    return max(range(nA), key=lambda x: (min(U(x, b) for b in range(nB)), x == myF(0), -x))

def match(g, X, Y):
    """Row X vs column Y.  Returns (table X, table Y, expected payoffs)."""
    tx, ty = policy(g, X, Y, 0), policy(g, Y, X, 1)
    tot, n = [0.0, 0.0], 0
    for p in range(len(tx)):
        for a in tx[p]:
            for b in ty[p]:
                u = g.U[(a, b)]; tot[0] += u[0]; tot[1] += u[1]; n += 1
    return tx, ty, (tot[0] / n, tot[1] / n)

def dist(g, tab, role):
    d = [0] * g.n(role)
    for row in tab:
        for v in row: d[v] += 1
    tot = sum(d); return {g.acts[role][i]: round(x / tot, 3) for i, x in enumerate(d) if x}

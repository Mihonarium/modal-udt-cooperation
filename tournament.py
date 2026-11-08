"""Round-robin tournament of idealised modal agents in the randomised exact evaluator (rmodal), with the bounded
bots' (bounded7.py) payoffs at every budget pair read off the same chains (bounded_tournament.json).

Every agent meets every agent (itself included) in both seats of every game.  Scores per game are normalised to the
matrix's payoff range for the seat, (ev - min U) / (max U - min U), so Chicken's -100 does not swamp the rest; the
raw figures are kept too.  Output: tournament.json, tournament.txt.   python3 tournament.py [n_random_2x2] [n_random_3x3]
"""
import json, sys, time
from itertools import product
from rmodal import *
from v5 import V5, V5R, fair_point, maxmin_val
from v6 import V6
from v7 import V7
from run import G, rand_game

NR = int(sys.argv[1]) if len(sys.argv) > 1 else 20
NR3 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
RND = R(npub=2, k=1, m=10)

def PD(T, R_, P, S): return G(f"PD{T}/{R_}/{P}/{S}", (["C", "D"],) * 2, [[(R_, R_), (S, T)], [(T, S), (P, P)]])
NAMED = [PD(5, 3, 1, 0), PD(3, 2, 1, 0), PD(4, 3, 2, 1), PD(10, 3, 1, 0),
         G("StagHunt", (["S", "H"],) * 2, [[(4, 4), (0, 3)], [(3, 0), (3, 3)]]),
         G("Chicken", (["Sw", "DS"],) * 2, [[(0, 0), (-1, 5)], [(5, -1), (-100, -100)]]),
         G("Chicken-mild", (["Sw", "St"],) * 2, [[(3, 3), (1, 4)], [(4, 1), (0, 0)]]),
         G("BoS", (["A", "B"],) * 2, [[(2, 1), (0, 0)], [(0, 0), (1, 2)]]),
         G("Coord", (["A", "B"],) * 2, [[(1, 1), (0, 0)], [(0, 0), (1, 1)]]),
         G("CoordRanked", (["A", "B"],) * 2, [[(2, 2), (0, 0)], [(0, 0), (1, 1)]]),
         G("MatchingPennies", (["H", "T"],) * 2, [[(1, -1), (-1, 1)], [(-1, 1), (1, -1)]]),
         G("Asym", (["A", "B"],) * 2, [[(10, 0), (1, 1)], [(1, 1), (1, 1)]])]

# ---- game-generic helper roles -------------------------------------------------------------------------------
def mm_act(g, role): return max(range(g.n(role)), key=lambda a: (min(g.u(role, a, b) for b in range(g.n(1 - role))), -a))
def threat_act(g, role):
    """The action this seat would profit most from committing to against a best-responder."""
    nA, nB = g.n(role), g.n(1 - role)
    return max(range(nA), key=lambda a: (g.u(role, a, max(range(nB), key=lambda b: (g.u(1 - role, b, a), -b))), -a))
def best_resp(g, role, b): return max(range(g.n(role)), key=lambda a: (g.u(role, a, b), -a))

class Stone(RAgent):
    """Commits to a role-dependent action chosen by `pick(g, role)`."""
    def __init__(self, pick, name): super().__init__(name); self.pick = pick
    def program(self, g, role, me, opp, r, ctx): return [], self.pick(g, role)

class FairStone(RAgent):
    """Plays its part of the fair point unconditionally."""
    def __init__(self, name="FairStone"): super().__init__(name)
    def program(self, g, role, me, opp, r, ctx):
        pr, pc, uv, _ = fair_point(g, ctx.rnd.npub); return [], (pr, pc)[role](r[0])

class Mixer(RAgent):
    """Private mix: its threat action w.p. 0.9, else its fair action (unreadable at K = 1)."""
    def __init__(self, name="Mixer"): super().__init__(name)
    def program(self, g, role, me, opp, r, ctx):
        pr, pc, uv, _ = fair_point(g, ctx.rnd.npub)
        return [], threat_act(g, role) if r[2] < 9 else (pr, pc)[role](r[0])

class Clique(RAgent):
    """Exact-copy checker: plays its part of the fair point iff the opponent is an exact copy (same class and the
    same fallback), otherwise `other(g, role)`.  The modal analogue of comparing source code: no proof search at all.
    other = mm_act gives CliqueBot (fair with its own kind, maxmin with everyone else); other = threat_act gives the
    cartel (fair with its own kind, the threat action against everyone else)."""
    def __init__(self, other, name): super().__init__(name); self.other = other
    def program(self, g, role, me, opp, r, ctx):
        o = opp[0]
        if type(o) is Clique and o.other is self.other:
            pr, pc, uv, _ = fair_point(g, ctx.rnd.npub); return [], (pr, pc)[role](r[0])
        return [], self.other(g, role)

class FB(RAgent):
    """FairBot aimed at the fair point; fallback given by `fb(g, role)`."""
    def __init__(self, fb, name): super().__init__(name); self.fb = fb; self._c = {}
    def program(self, g, role, me, opp, r, ctx):
        pr, pc, uv, _ = fair_point(g, ctx.rnd.npub); myF, opF = (pr, pc)[role], (pr, pc)[1 - role]
        if (me, opp) not in self._c: self._c[(me, opp)] = Box(ctx.plays(opp, opF))
        return [(self._c[(me, opp)], myF(r[0]))], self.fb(g, role)

class PB(RAgent):
    """PrudentBot aimed at the fair point: F iff Box(opp F) and, for each exploitable (a, b), Box_1(opp does not play b
    against Const_a at every key); fallback maxmin."""
    def __init__(self, name="PrudentBot"): super().__init__(name); self._c = {}; self._k = {}
    def const(self, a):
        if a not in self._k: self._k[a] = RConst(a, f"PB-Const{a}")
        return self._k[a]
    def program(self, g, role, me, opp, r, ctx):
        pr, pc, uv, _ = fair_point(g, ctx.rnd.npub); myF, opF = (pr, pc)[role], (pr, pc)[1 - role]
        if (me, opp) not in self._c:
            nA, nB = g.n(role), g.n(1 - role); probes = []
            for b in range(nB):
                a = best_resp(g, role, b)
                if g.u(role, a, b) > uv[role]:
                    probes.append(Box(Not(ctx.plays((opp[0], self.const(a), 1 - role), lambda p, b=b: b)), 1))
            self._c[(me, opp)] = And(Box(ctx.plays(opp, opF)), *probes)
        return [(self._c[(me, opp)], myF(r[0]))], mm_act(g, role)

class Punisher(RAgent):
    """'Be provably a rock or I commit': gives in (best-responds) iff PA proves the opponent plays its threat action at
    every key against me; otherwise plays its own threat action.  Generalises the Chicken SIC(PA, Straight)."""
    def __init__(self, name="Punisher"): super().__init__(name); self._c = {}
    def program(self, g, role, me, opp, r, ctx):
        tb = threat_act(g, 1 - role)
        if (me, opp) not in self._c: self._c[(me, opp)] = Box(ctx.plays(opp, lambda p: tb))
        return [(self._c[(me, opp)], best_resp(g, role, tb))], threat_act(g, role)

class BestResponder(V6):
    """CDT-like reader: best-responds to a provable commitment, never gives in, maxmin otherwise.  No reciprocation."""
    def __init__(self, name="BestResponder"): super().__init__(name, rock="never")
    def respond(self, g, role, q, myF_p, rnd):
        nA, nB = g.n(role), g.n(1 - role); myev = lambda a: sum(q[b] * g.u(role, a, b) for b in range(nB))
        a = max(range(nA), key=lambda x: (myev(x), -x)); return a, a, rnd.m
    def program(self, g, role, me, opp, r, ctx):
        dl, d = V6.program(self, g, role, me, opp, r, ctx)
        return dl[1:], mm_act(g, role)   # drop B'

class V34(RAgent):
    """The repo's Version 3-B and Version 4 (v3.py, v4.py) in the randomised evaluator.  Outcomes (a, b) with my
    payoff u are tiered by the pure maxmins: cooperative (u >= m_me, v >= m_opp, one strictly better), exploitative
    (v < m_opp), neutral.  Each gives the check Box(at every key: I play a -> my payoff is at least u).  V3-B: all
    cooperative and neutral checks first (best u first, in PA), exploitative checks last in PA+1; fallback maxmin.
    V4: a cooperative check whose b could be exploited also needs the probe Box_1(the opponent does not play b at
    every key against the constant that exploits it); then exploitative checks in PA+1, then neutral."""
    def __init__(self, name="V4", v4=True): super().__init__(name); self.v4 = v4; self._c = {}; self._k = {}
    def const(self, a):
        if a not in self._k: self._k[a] = RConst(a, f"{self.name}-Ex{a}")
        return self._k[a]
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._c:
            nA, nB = g.n(role), g.n(1 - role)
            U = lambda a, b: g.u(role, a, b); V = lambda a, b: g.u(1 - role, b, a)
            mm = lambda rr: max(min(g.u(rr, x, y) for y in range(g.n(1 - rr))) for x in range(g.n(rr)))
            m_me, m_op = mm(role), mm(1 - role)
            best = lambda b: max(range(nA), key=lambda x: (U(x, b), -x))
            groups = {"coop": [], "neutral": [], "exploit": []}
            for a in range(nA):
                for b in range(nB):
                    u, v = U(a, b), V(a, b)
                    if u < m_me: continue
                    groups["exploit" if v < m_op else ("coop" if (u > m_me or v > m_op) else "neutral")].append((u, a, b))
            def ge(a, u):
                good = [y for y in range(nB) if U(a, y) >= u]
                return And(*[Imp(Var(k, a), Or(*[Var(ko, y) for y in good])) for k, ko in zip(ctx.keys(me), ctx.keys(opp))])
            dl, seen = [], set()
            for u, a, b in sorted(groups["coop"], key=lambda c: (-c[0], c[1], c[2])):
                ax = best(b)
                if self.v4 and U(ax, b) > U(a, b):
                    dl.append((And(Box(ge(a, u)), Box(Not(ctx.plays((opp[0], self.const(ax), 1 - role), lambda p, b=b: b)), 1)), a))
                elif not self.v4 and (u, a, 0) not in seen:
                    seen.add((u, a, 0)); dl.append((Box(ge(a, u)), a))
                else: dl.append((Box(ge(a, u)), a))
            order = (("exploit", 1), ("neutral", 0)) if self.v4 else (("neutral", 0), ("exploit", 1))
            for grp, th in order:
                for u, a, b in sorted(groups[grp], key=lambda c: (-c[0], c[1])):
                    if (u, a, th) in seen: continue
                    seen.add((u, a, th)); dl.append((Box(ge(a, u), th), a))
            self._c[(me, opp)] = dl
        return self._c[(me, opp)], mm_act(g, role)

class GreedyUDT(RAgent):
    """The repo's greedy modal UDT in the randomised evaluator: for each payoff level u from best to worst and each
    action a, play a if Box_0(at every key: I play a -> my payoff is at least u); else maxmin.  (The level-u check
    for the maxmin action is trivially provable at u = maxmin, so it never gets less than its maxmin.)"""
    def __init__(self, name="GreedyUDT"): super().__init__(name); self._c = {}
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._c:
            nA, nB = g.n(role), g.n(1 - role); lst = []
            for u in sorted({g.u(role, a, b) for a in range(nA) for b in range(nB)}, reverse=True):
                for a in range(nA):
                    good = [b for b in range(nB) if g.u(role, a, b) >= u]
                    if not good: continue
                    body = And(*[Imp(Var(k, a), Or(*[Var(ko, b) for b in good])) for k, ko in zip(ctx.keys(me), ctx.keys(opp))])
                    lst.append((Box(body), a))
            self._c[(me, opp)] = lst
        return self._c[(me, opp)], mm_act(g, role)

AGENTS = {
    "V7": lambda n="V7": V7(n),
    "V7-norock": lambda n="V7-norock": V7(n, rock="never"),
    "V6": lambda n="V6": V6(n),
    "V6-norock": lambda n="V6-norock": V6(n, rock="never"),
    "V5R": lambda n="V5R": V5R(n),
    "V5": lambda n="V5": V5(n),
    "FairBot": lambda n="FairBot": FB(mm_act, n),
    "PrudentBot": lambda n="PrudentBot": PB(n),
    "StubbornFB": lambda n="StubbornFB": FB(threat_act, n),
    "Punisher": lambda n="Punisher": Punisher(n),
    "BestResponder": lambda n="BestResponder": BestResponder(n),
    "V4": lambda n="V4": V34(n, v4=True),
    "V3B": lambda n="V3B": V34(n, v4=False),
    "GreedyUDT": lambda n="GreedyUDT": GreedyUDT(n),
    "CliqueBot": lambda n="CliqueBot": Clique(mm_act, n),
    "Cartel": lambda n="Cartel": Clique(threat_act, n),
    "FairStone": lambda n="FairStone": FairStone(n),
    "ThreatStone": lambda n="ThreatStone": Stone(threat_act, n),
    "MaxminStone": lambda n="MaxminStone": Stone(mm_act, n),
    "Mixer": lambda n="Mixer": Mixer(n),
}

INF = 10 ** 9
BUD = [0, 1, 2, 3, 4, 6, INF]          # depth budgets of the bounded bots (bounded7.py); INF = idealised
GROUP_OF = lambda gn: "pd" if gn.startswith("PD") else {"StagHunt": "stag", "Chicken": "chicken", "Chicken-mild": "mild", "BoS": "bos", "Coord": "coord", "CoordRanked": "coord", "MatchingPennies": "pennies", "Asym": "asym"}.get(gn, "r2" if gn.startswith("r2") else "r3")

def run():
    t0 = time.time()
    games = NAMED + [rand_game(f"r2-{s}", 2, s) for s in range(1000, 1000 + NR)] + [rand_game(f"r3-{s}", 3, s) for s in range(1000, 1000 + NR3)]
    names = list(AGENTS); n = len(names); ix = {nm: i for i, nm in enumerate(names)}
    results = {}   # game -> row agent -> col agent -> (ev_row, ev_col)      (idealised = budget INF)
    stabs = {}     # game -> row agent -> col agent -> (pair stabilisation level, row's own, col's own)
    # bounded: per game group, per (row budget, col budget): normalised payoff of row agent i at budget Dx against
    # col agent j at budget Dy, summed over the group's games and both seats (divided by counts at the end)
    bud = {}; budn = {}
    for gi, g in enumerate(games):
        ctx = RCtx(g, RND); results[g.name] = {}; stabs[g.name] = {}
        lo = (min(u[0] for u in g.U.values()), min(u[1] for u in g.U.values())); hi = (max(u[0] for u in g.U.values()), max(u[1] for u in g.U.values()))
        rngs = ((hi[0] - lo[0]) or 1.0, (hi[1] - lo[1]) or 1.0)
        grp = GROUP_OF(g.name)
        if grp not in bud:
            bud[grp] = {f"{a},{b}": [[0.0] * n for _ in range(n)] for a in BUD for b in BUD}; budn[grp] = 0
        budn[grp] += 1
        for xn in names:
            results[g.name][xn] = {}; stabs[g.name][xn] = {}
            for yn in names:
                X = AGENTS[xn](xn + "#r"); Y = AGENTS[yn](yn + "#c")
                seq, s = rplay(g, X, Y, ctx, N=60, trace=True)
                ev = expected(g, seq[-1][0], seq[-1][1], RND); results[g.name][xn][yn] = ev
                sx = next(i for i in range(len(seq)) if all(seq[j][0] == seq[-1][0] for j in range(i, len(seq))))
                sy = next(i for i in range(len(seq)) if all(seq[j][1] == seq[-1][1] for j in range(i, len(seq))))
                stabs[g.name][xn][yn] = (s, sx, sy)
                pol = {D: (seq[min(D, len(seq) - 1)][0], seq[min(D, len(seq) - 1)][1]) for D in BUD}
                for Dx in BUD:
                    for Dy in BUD:
                        e = expected(g, pol[Dx][0], pol[Dy][1], RND)
                        bud[grp][f"{Dx},{Dy}"][ix[xn]][ix[yn]] += (e[0] - lo[0]) / rngs[0]     # row seat
                        bud[grp][f"{Dy},{Dx}"][ix[yn]][ix[xn]] += (e[1] - lo[1]) / rngs[1]     # column seat
        print(f"[{gi+1}/{len(games)}] {g.name} done  {time.time()-t0:.0f}s", flush=True)
        json.dump(dict(games=[g.name for g in games[:gi+1]], results=results, stabs=stabs), open("tournament.json", "w"))
    for grp in bud:
        for k in bud[grp]:
            bud[grp][k] = [[round(v / (2 * budn[grp]), 4) for v in row] for row in bud[grp][k]]
    json.dump(dict(names=names, budgets=[("inf" if D == INF else D) for D in BUD], groups={grp: budn[grp] for grp in bud},
                   matrices={grp: {k.replace(str(INF), "inf"): m for k, m in bud[grp].items()} for grp in bud}), open("bounded_tournament.json", "w"))
    # scoring
    lo = {g.name: (min(u[0] for u in g.U.values()), min(u[1] for u in g.U.values())) for g in games}
    hi = {g.name: (max(u[0] for u in g.U.values()), max(u[1] for u in g.U.values())) for g in games}
    fair = {g.name: fair_point(g, RND.npub)[2] for g in games}
    score = {n: [] for n in names}; raw = {n: [] for n in names}; atfair = {n: 0 for n in names}; cells = 0
    pergame = {g.name: {} for g in games}
    for g in games:
        gn = g.name; tot = {n: [] for n in names}
        for xn in names:
            for yn in names:
                ev = results[gn][xn][yn]
                if ev[0] is None: continue
                for seat, n in ((0, xn), (1, yn)):
                    rng = hi[gn][seat] - lo[gn][seat] or 1.0
                    tot[n].append((ev[seat] - lo[gn][seat]) / rng); raw[n].append(ev[seat])
                    if n == xn and seat == 0: pass
        for n in names:
            m = sum(tot[n]) / len(tot[n]); pergame[gn][n] = m; score[n].append(m)
    ranks = {n: [] for n in names}
    for gn in pergame:
        order = sorted(names, key=lambda n: -pergame[gn][n])
        for i, n in enumerate(order): ranks[n].append(i + 1)
    board = sorted(names, key=lambda n: -sum(score[n]) / len(score[n]))
    lines = [f"Round-robin, {len(games)} games ({len(NAMED)} named + {NR} random 2x2 + {NR3} random 3x3), {len(names)} agents, both seats, self-play included.",
             "Score = payoff normalised to the matrix's range for the seat, averaged over opponents and seats, then over games.", "",
             f"{'agent':14s} {'score':>6s} {'avg rank':>9s} {'named':>6s} {'random':>7s}   per named game: " + " ".join(f"{g.name[:7]:>7s}" for g in NAMED)]
    for n in board:
        named = [pergame[g.name][n] for g in NAMED]; rnd_ = [pergame[g.name][n] for g in games[len(NAMED):]]
        lines.append(f"{n:14s} {sum(score[n])/len(score[n]):6.3f} {sum(ranks[n])/len(ranks[n]):9.2f} {sum(named)/len(named):6.3f} {(sum(rnd_)/len(rnd_) if rnd_ else 0):7.3f}   " + " ".join(f"{v:7.3f}" for v in named))
    # head-to-head in Chicken and PD
    for gn in ("Chicken", "PD5/3/1/0"):
        lines += ["", f"{gn}: row agent's expected payoff against each column agent (row seat)", f"{'':14s}" + "".join(f"{n[:9]:>10s}" for n in names)]
        for xn in names:
            lines.append(f"{xn:14s}" + "".join(f"{(results[gn][xn][yn][0] if results[gn][xn][yn][0] is not None else float('nan')):10.2f}" for yn in names))
    out = "\n".join(lines); print(out); open("tournament.txt", "w").write(out + "\n")
    json.dump(dict(games=[g.name for g in games], results=results, stabs=stabs, pergame=pergame, board=board), open("tournament.json", "w"))
    print(f"{time.time()-t0:.0f}s")

if __name__ == "__main__":
    run()

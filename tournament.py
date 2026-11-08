"""Round-robin tournament of idealised modal agents in the randomised exact evaluator (rmodal).

Every agent meets every agent (itself included) in both seats of every game.  Scores per game are normalised to the
matrix's payoff range for the seat, (ev - min U) / (max U - min U), so Chicken's -100 does not swamp the rest; the
raw figures are kept too.  Output: tournament.json, tournament.txt.   python3 tournament.py [n_random_2x2] [n_random_3x3]
"""
import json, sys, time
from itertools import product
from rmodal import *
from v5 import V5, V5R, fair_point, maxmin_val
from v6 import V6
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
    "V6": lambda n="V6": V6(n),
    "V6-norock": lambda n="V6-norock": V6(n, rock="never"),
    "V5R": lambda n="V5R": V5R(n),
    "V5": lambda n="V5": V5(n),
    "FairBot": lambda n="FairBot": FB(mm_act, n),
    "PrudentBot": lambda n="PrudentBot": PB(n),
    "StubbornFB": lambda n="StubbornFB": FB(threat_act, n),
    "Punisher": lambda n="Punisher": Punisher(n),
    "BestResponder": lambda n="BestResponder": BestResponder(n),
    "GreedyUDT": lambda n="GreedyUDT": GreedyUDT(n),
    "FairStone": lambda n="FairStone": FairStone(n),
    "ThreatStone": lambda n="ThreatStone": Stone(threat_act, n),
    "MaxminStone": lambda n="MaxminStone": Stone(mm_act, n),
    "Mixer": lambda n="Mixer": Mixer(n),
}

def run():
    t0 = time.time()
    games = NAMED + [rand_game(f"r2-{s}", 2, s) for s in range(1000, 1000 + NR)] + [rand_game(f"r3-{s}", 3, s) for s in range(1000, 1000 + NR3)]
    names = list(AGENTS)
    results = {}   # game -> row agent -> col agent -> (ev_row, ev_col)
    for gi, g in enumerate(games):
        ctx = RCtx(g, RND); results[g.name] = {}
        for xn in names:
            results[g.name][xn] = {}
            for yn in names:
                X = AGENTS[xn](xn + "#r"); Y = AGENTS[yn](yn + "#c")
                try:
                    px, py, s, ev = rplay(g, X, Y, ctx, N=60)
                except AssertionError as e:
                    ev = (None, None)
                results[g.name][xn][yn] = ev
        print(f"[{gi+1}/{len(games)}] {g.name} done  {time.time()-t0:.0f}s", flush=True)
        json.dump(dict(games=[g.name for g in games[:gi+1]], results=results), open("tournament.json", "w"))
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
        lines.append(f"{n:14s} {sum(score[n])/len(score[n]):6.3f} {sum(ranks[n])/len(ranks[n]):9.2f} {sum(named)/len(named):6.3f} {sum(rnd_)/len(rnd_):7.3f}   " + " ".join(f"{v:7.3f}" for v in named))
    # head-to-head in Chicken and PD
    for gn in ("Chicken", "PD5/3/1/0"):
        lines += ["", f"{gn}: row agent's expected payoff against each column agent (row seat)", f"{'':14s}" + "".join(f"{n[:9]:>10s}" for n in names)]
        for xn in names:
            lines.append(f"{xn:14s}" + "".join(f"{(results[gn][xn][yn][0] if results[gn][xn][yn][0] is not None else float('nan')):10.2f}" for yn in names))
    out = "\n".join(lines); print(out); open("tournament.txt", "w").write(out + "\n")
    json.dump(dict(games=[g.name for g in games], results=results, pergame=pergame, board=board), open("tournament.json", "w"))
    print(f"{time.time()-t0:.0f}s")

if __name__ == "__main__":
    run()

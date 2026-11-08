"""Bounded, runnable agents for the WHOLE design: simulation towers with a depth budget.

A bounded bot is a program given as a spec line (its source) plus a budget D:
    "V7 rock=auto"   "V6 rock=never"   "V5R"   "FairBot"   "PrudentBot"   "Punisher"   "STONE threat"  ...
Run against an opponent's source, it builds both decision lists from the two specs and the payoff matrix (the same
code the idealised agents use, `tournament.AGENTS`), and decides every "PA+k proves phi" by SIMULATION: it runs
both programs at depths k, k+1, ..., D-1 (each of which runs both programs at the depths below it) and checks that
phi held at every one of those depths.  At depth 0 nothing is run and every box counts as true: the trusting base
case.  That is where the design's vacuous-truth conventions live (reciprocate at the bottom; be a rock at the
bottom in gated games), and the consistency guards Con_k on the commitment reader are exactly the places where the
design refuses to trust the bottom.  Every run halts, because the depth decreases with each nested simulation.

Theorem (checked by test_bounded7.py on every pair of the field, every level): the bounded bot with budget D plays
the Kripke chain's level D for that pair.  So a bot whose budget is at least the chain's stabilisation depth plays
the idealised fixed point exactly, and one below it plays the transient; the idealised agent is the limit D -> inf.
Against an opponent with another budget D', the bot's simulation still descends from its own D one depth per
level (it runs the opponent's CODE, not the opponent's budget), so the match outcome is (level D of X, level D' of
Y) of the one chain the two codes define.

Relation to the proof-search bots of bounded.py (BPC): there a budget counts nested necessitations in a small
formal system whose bottom proves nothing, so FairBot_0 defects and FairBot_k cooperates from k = 1.  Here the
bottom trusts: FairBot_0 cooperates with everyone, DefectBot included, and is right from k = 1.  BPC cannot be
scaled to this design (per match it would need hundreds of box atoms across six theories and Loeb-shaped fixed
points over 2^20 joint policies; its PD-only tournament already took 2.7 CPU-hours).  The simulation tower is the
bounded formalism in which the whole design runs as a program, and it agrees with the exact evaluator by
construction rather than by a separate proof search.
"""
import sys
from modal import Top, Bot, Var, Not, And, Or, Box
from rmodal import RCtx, R, RAgent, RConst, expected

INF = 10 ** 9

def make(spec, name=None):
    """Instantiate an agent from its source line (the spec).  Unknown sources raise: nothing is assumed about them."""
    import tournament as T
    parts = spec.split()
    head, kw = parts[0], dict(p.split("=") for p in parts[1:])
    if head not in T.AGENTS: raise ValueError(f"unknown program: {spec!r}")
    bot = T.AGENTS[head](name or spec)
    for k, v in kw.items():
        if not hasattr(bot, k): raise ValueError(f"{head}: unknown parameter {k}")
        setattr(bot, k, v)
    return bot

class Tower:
    """The simulation tower for one match: X (row) vs Y (column), both as agent objects built from their specs."""
    def __init__(self, game, X, Y, rnd):
        self.g, self.X, self.Y, self.ctx = game, X, Y, RCtx(game, rnd)
        self.progs, self.memo, self.boxmemo = {}, {}, {}
    def prog(self, key):
        """Decision list and default of the program at `key` = (agent, opponent, role, r_pub, r_c, r_f)."""
        if key not in self.progs:
            A, B, role = key[:3]
            dl, d = A.program(self.g, role, key[:3], (B, A, 1 - role), key[3:], self.ctx)
            self.progs[key] = (dl, d)
        return self.progs[key]
    def out(self, key, d):
        """What the program at `key` outputs when run with depth budget d.  Halts: boxes only look below d."""
        mk = (key, d)
        if mk in self.memo: return self.memo[mk]
        dl, default = self.prog(key)
        act = default
        for c, a in dl:
            if self.holds(c, d): act = a; break
        self.memo[mk] = act
        return act
    def holds(self, f, d):
        """Truth of a decision-list condition for a run at depth d.  Only boxes look at other depths."""
        if isinstance(f, Top): return True
        if isinstance(f, Bot): return False
        if isinstance(f, Not): return not self.holds(f.x, d)
        if isinstance(f, And): return all(self.holds(x, d) for x in f.xs)
        if isinstance(f, Or): return any(self.holds(x, d) for x in f.xs)
        if isinstance(f, Box):
            # PA+k proves phi, for a budget-d bot: phi held at every simulated depth j with k <= j < d
            mk = (id(f), d)
            if mk in self.boxmemo: return self.boxmemo[mk]
            if d <= f.k: r = True
            else: r = self.holds(f, d - 1) and self.truth(f.x, d - 1)
            self.boxmemo[mk] = r
            return r
        raise TypeError(f)
    def truth(self, f, j):
        """Truth of a formula about the programs' outputs at depth j (the inside of a box)."""
        if isinstance(f, Top): return True
        if isinstance(f, Bot): return False
        if isinstance(f, Var): return self.out(f.key, j) == f.a
        if isinstance(f, Not): return not self.truth(f.x, j)
        if isinstance(f, And): return all(self.truth(x, j) for x in f.xs)
        if isinstance(f, Or): return any(self.truth(x, j) for x in f.xs)
        if isinstance(f, Box): return self.holds(f, j)
        raise TypeError(f)
    def policy(self, role, d):
        """The whole policy (draw -> action) of the row (role 0) or column (role 1) bot run with budget d."""
        base = (self.X, self.Y, 0) if role == 0 else (self.Y, self.X, 1)
        return {k[3:]: self.out(k, d) for k in self.ctx.keys(base)}

def run(game, specX, specY, DX, DY, rnd):
    """Row bot specX with budget DX against column bot specY with budget DY.  Returns (policy X, policy Y, EV)."""
    X, Y = make(specX, "X"), make(specY, "Y")
    tw = Tower(game, X, Y, rnd)
    px, py = tw.policy(0, DX), tw.policy(1, DY)
    return px, py, expected(game, px, py, rnd)

if __name__ == "__main__":
    import tournament as T
    g = T.NAMED[5]   # Chicken
    rnd = T.RND
    for specX, specY, DX, DY in [("V7", "V7", 3, 3), ("V7", "V7", 0, 0), ("V7", "V7", 1, 6), ("FairBot", "ThreatStone", 0, 0), ("FairBot", "ThreatStone", 1, 0),
                                 ("V7", "ThreatStone", 1, 0), ("V7", "ThreatStone", 2, 0), ("V7", "ThreatStone", 6, 0), ("V7", "Punisher", 4, 4)]:
        try:
            px, py, ev = run(g, specX, specY, DX, DY, rnd)
            print(f"{g.name}: {specX}@{DX} vs {specY}@{DY}: EV {ev}")
        except ValueError as e: print(e)

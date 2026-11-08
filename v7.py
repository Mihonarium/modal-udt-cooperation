"""V7 = V6 plus a Löb tier AFTER reciprocation.

  Löb_2  for the most profitable exploitable pair (a, b):   Box_2( I play a at every key -> the opponent plays b at
         every key )  -> play a.
         Unguarded, so it passes vacuously at the first levels where reciprocation has failed; an opponent that reads
         commitments at PA+1 behind a consistency guard (a best-responder, or this agent's own C tier) sees "a at every
         key" at level 1, answers b from level 2, and Löb closes the loop: PA+2 proves "if I play a, it plays b".
         Read in PA+2 rather than PA because such a reader cannot answer before level 2; read in PA+2 rather than
         higher because every extra stratum is another level of vacuous a-play against everyone.
         Placed after B', so it never touches an opponent that reciprocates (copies, FairBot, PrudentBot, the
         stubborn reciprocator): B' fires at level 0 and stays.  The same check placed BEFORE reciprocation makes the
         agent unverifiable to a PA-reasoner (its cooperation would rest on "my exploit search fails"); after it, the
         agent's F-play is still PA-provable to anyone it reciprocates with.
         Against a stone, a mixer or a PA-level punisher the tier passes vacuously for two levels and dies; C then
         answers as before.  Those two levels are visible to anyone probing in PA+1 how we play against a constant,
         so the tier is gated off in games where a is also my best response to one of the opponent's threats
         (there it would read as giving in); in the PD, Chicken and Battle of the Sexes it is on.  The level-0 rock (gated games) stays first: it is for readers at PA level, which Löb_2
         cannot reach because they need the agent's level-0 play.
"""
from rmodal import *
from v6 import V6

class V7(V6):
    def __init__(self, name="V7", **kw): super().__init__(name, **kw)
    def build(self, g, role, me, opp, ctx):
        s = V6.build(self, g, role, me, opp, ctx)
        nA, nB = g.n(role), g.n(1 - role)
        U = lambda a, b: g.u(role, a, b)
        uF = self.fairpoint(g, ctx)[2][role]
        V = lambda a, b: g.u(1 - role, b, a); vF = self.fairpoint(g, ctx)[2][1 - role]
        best = None
        for b in range(nB):
            a = max(range(nA), key=lambda x: (U(x, b), -x))
            if U(a, b) > uF and (best is None or U(a, b) > best[0]): best = (U(a, b), a, b)
        # gate: the tier plays a for two vacuous levels against every non-reciprocator, the constant stones that
        # others probe us against included.  If a is also my best response to some opponent commitment b' that
        # would pay it more than fair, a probe at PA+1 reads those levels as giving in to b' and refuses to
        # reciprocate (r3-1016 and r2-1025 in the random set cost copies the fair point before this gate).
        give_in = {max(range(nA), key=lambda x: (U(x, b2), -x)) for b2 in range(nB)
                   if V(max(range(nA), key=lambda x: (U(x, b2), -x)), b2) > vF + 1e-9}
        if best and best[1] in give_in: best = None
        s["L"] = [(Box(Imp(ctx.plays(me, lambda p, a=a: a), ctx.plays(opp, lambda p, b=b: b)), 2), a)
                  for _, a, b in ([best] if best else [])]
        return s
    def program(self, g, role, me, opp, r, ctx):
        if (me, opp) not in self._cache: self._cache[(me, opp)] = self.build(g, role, me, opp, ctx)
        s = self._cache[(me, opp)]; p, c, f = r
        dl = list(s["R"]) + [(s["B"], s["myF"](p))] + list(s["L"])
        dl += [(cond, a_star if f < pm else a_ref) for _, cond, a_star, a_ref, pm in s["C"][p]]
        return dl, self.pick(s["D"][p], f)

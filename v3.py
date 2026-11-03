"""Version 3: utility-ordered modal UDT with per-outcome proof tiers.
Each outcome o=(a,b) with my utility u gives the check "I play a -> my payoff >= u".
Tier of o (m = pure maxmin values):  coop    : U_me>=m_me, U_opp>=m_opp, and strictly better for one
                                     exploit : U_opp < m_opp   (good for me at the opponent's expense)
                                     neutral : everything else (e.g. the maxmin point itself)
coop/neutral checks use PA (Box_0). exploit checks use `xform`:
   'PA+1'   : Box_1(phi)  = Box(not Box bot -> phi)          (Kelvin's literal spec)
   'conPA'  : not Box bot  and  Box(phi)   (false at level 0 only; equal to Box(phi) in N)
   'conPA1' : not Box bot  and  Box_1(phi)
order: 'interleave' = utility-major, within a utility coop < neutral < exploit (spec);
       'exploit-last' = all coop/neutral checks (utility order) before any exploit check.
Fallback: maxmin action (reached only if no check passes). Checks with u < my maxmin are dropped,
so every play is >= my pure maxmin (soundness of PA / PA+1)."""
from modal import *

class V3(Agent):
    def __init__(self, name="V3", xform="PA+1", order="interleave", rev=False):
        super().__init__(name); self.xform, self.order, self.rev = xform, order, rev
    def program(self, g, role, me, opp, ctx):
        nA, nB = g.n(role), g.n(1 - role)
        acts = list(range(nA))[::-1] if self.rev else list(range(nA))
        mm = lambda r: max(min(g.u(r, x, y) for y in range(g.n(1 - r))) for x in range(g.n(r)))
        m_me, m_op = mm(role), mm(1 - role)
        rank = {"coop": 0, "neutral": 1, "exploit": 2}
        checks = []
        for a in acts:
            for b in range(nB):
                u, v = g.u(role, a, b), g.u(1 - role, b, a)
                if v < m_op: t = "exploit"
                elif u >= m_me and (u > m_me or v > m_op): t = "coop"
                else: t = "neutral"
                checks.append((u, t, a))
        key = ((lambda c: (-c[0], rank[c[1]], acts.index(c[2]))) if self.order == "interleave"
               else (lambda c: (c[1] == "exploit", -c[0], rank[c[1]], acts.index(c[2]))))
        seen, dl = set(), []
        for u, t, a in sorted(checks, key=key):
            if (u, t, a) in seen or u < m_me: continue   # floor: checks below my maxmin are never useful
            seen.add((u, t, a))
            good = [b for b in range(nB) if g.u(role, a, b) >= u]
            phi = Imp(Var(me, a), Or(*[Var(opp, b) for b in good]))
            if t != "exploit": c = Box(phi)
            elif self.xform == "PA+1": c = Box(phi, 1)
            elif self.xform == "conPA": c = And(Not(Box(Bot())), Box(phi))
            else: c = And(Not(Box(Bot())), Box(phi, 1))
            dl.append((c, a))
        maxmin_a = max(range(nA), key=lambda x: (min(g.u(role, x, y) for y in range(nB)), -x))
        return dl, maxmin_a

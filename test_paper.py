"""Reproduce Barasz et al. 2014 outcomes (Thms 3.1, 3.2, the PB-CB level-2 remark) on the PD."""
from modal import *

C, D = 0, 1
PD = Game("PD", (["C", "D"], ["C", "D"]),
          {(0, 0): (2, 2), (0, 1): (0, 3), (1, 0): (3, 0), (1, 1): (1, 1)})
ctx = Ctx(PD, coop_target=(C, C), fallback=(D, D))
CB, DB = Const(C, "CB"), Const(D, "DB")
ctx.consts = {C: CB, D: DB}
FB, PB = FairBot(), PrudentBot()
name = "CD"
expected = {  # (row, col) -> (row action, col action) ; from the paper
    ("FB", "FB"): "CC", ("FB", "CB"): "CC", ("FB", "DB"): "DD",
    ("PB", "PB"): "CC", ("PB", "FB"): "CC", ("FB", "PB"): "CC",
    ("PB", "CB"): "DC", ("PB", "DB"): "DD", ("CB", "PB"): "CD",
}
ag = {a.name: a for a in [FB, PB, CB, DB]}
ok = True
for (x, y), e in expected.items():
    r, c, s = play(PD, ag[x], ag[y], ctx)
    got = name[r] + name[c]
    print(f"{x:>3} vs {y:<3} -> {got}  stabilises at level {s}   expected {e}  {'OK' if got == e else 'FAIL'}")
    ok &= got == e
seq, s = play(PD, PB, CB, ctx, trace=True)
print("PB vs CB by level:", [name[a] + name[b] for a, b in seq[:5]], "(paper: PA+2 |- PB(CB)=D)")
ok &= seq[0][0] == C and seq[1][0] == C and seq[2][0] == D
# Paper, after Thm 3.2: probing X(DB)=D in PA (not PA+1) makes PrudentBot lose self-cooperation.
class PB0(PrudentBot):
    def program(self, g, role, me, opp, ctx):
        (cond, a), = PrudentBot.program(self, g, role, me, opp, ctx)[0]
        cond.xs[1].k = 0
        return [(cond, a)], ctx.fallback(g)[role]
P0 = PB0(name="PB0")
r, c, s = play(PD, P0, P0, ctx)
print("PB-with-PA-probe vs itself ->", name[r] + name[c], "(paper: loses self-cooperation, expect DD)")
ok &= (r, c) == (D, D)
print("ALL OK" if ok else "SOME FAILED")

"""Cross-check: memoised Box evaluation vs the literal definition (phi at every level k <= m < n)."""
import modal
from modal import *
from run import rand_game, analysis
def run_all():
    out = []
    for n in (2, 3):
        for seed in range(2000, 2060):
            g = rand_game("x", n, seed); an = analysis(g); ctx = Ctx(g, an["target"], an["maxmin_act"])
            fb = lambda gg, r: an["maxmin_act"][r]
            V = [ModalUDT("U", default=fb), ModalUDT("E", default=0, exact=True), ModalUDT("S", default=fb, strat=True),
                 ModalUDT("R", default=fb, action_order=lambda k: list(range(k))[::-1]), ModalUDT("H", default=fb, chicken=True),
                 FairBot(), PrudentBot()]
            for X in V:
                for Y in V:
                    out.append(play(g, X, Y, ctx, N=60, trace=True)[0])
    return out
a = run_all()
modal.Box.ev = lambda self, val, n, memo: all(self.x.ev(val, m, memo) for m in range(self.k, n))
b = run_all()
print("pairs compared:", len(a), "level-sequences identical:", a == b)

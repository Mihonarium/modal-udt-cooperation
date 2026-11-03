"""PD with several payoff choices (T>R>P>S): self-play and cross-play of modal UDT variants."""
from modal import *
from run import G, analysis
rev = lambda n: [1, 0]
for (T, R, P, S) in [(3, 2, 1, 0), (5, 3, 1, 0), (4, 3, 2, 1), (10, 3, 1, 0), (3, 2, 0, -1), (101, 100, 1, 0)]:
    g = G(f"PD{T}{R}{P}{S}", (["C", "D"],) * 2, [[(R, R), (S, T)], [(T, S), (P, P)]])
    an = analysis(g); ctx = Ctx(g, (0, 0), (1, 1))
    V = [ModalUDT("base", default=1), ModalUDT("exact", default=1, exact=True), ModalUDT("revorder", default=1, action_order=rev),
         ModalUDT("chicken", default=1, chicken=True), ModalUDT("strat", default=1, strat=True),
         ModalUDT("exact-defC", default=0, exact=True)]
    line = []
    for i, X in enumerate(V):
        for Y in V[i:]:
            r, c, s = play(g, X, Y, ctx)
            line.append(f"{X.name}/{Y.name}:{'CD'[r]}{'CD'[c]}")
    for X in V:
        for Y in (FairBot(), PrudentBot()):
            r, c, s = play(g, X, Y, ctx)
            line.append(f"{X.name}/{Y.name}:{'CD'[r]}{'CD'[c]}")
    print(g.name, " ".join(line))

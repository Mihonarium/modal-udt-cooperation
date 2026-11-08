"""The bounded bot with budget D plays the Kripke chain's level D: checked for every ordered pair of the field,
in several games, at every level 0..LEVELS, against rmodal's trace.  Also prints each agent's stabilisation
depth (the budget from which it plays the idealised fixed point against everyone)."""
import time
from rmodal import rplay
import tournament as T
from bounded7 import Tower

LEVELS = 12
t0 = time.time(); names = list(T.AGENTS); cells = mism = 0; need = {n: 0 for n in names}
games = [T.NAMED[i] for i in (0, 4, 5, 6, 7, 10)] + [T.rand_game("r3-1016", 3, 1016), T.rand_game("r2-1025", 2, 1025)]
for g in games:
    for xn in names:
        for yn in names:
            X, Y = T.AGENTS[xn](xn + "#r"), T.AGENTS[yn](yn + "#c")
            seq, stab = rplay(g, X, Y, T.RCtx(g, T.RND), N=max(60, LEVELS + 2), trace=True)
            X2, Y2 = T.AGENTS[xn](xn + "#r"), T.AGENTS[yn](yn + "#c")
            tw = Tower(g, X2, Y2, T.RND)
            for d in range(LEVELS + 1):
                cells += 1
                if (tw.policy(0, d), tw.policy(1, d)) != seq[d]:
                    mism += 1
                    if mism <= 5: print(f"  MISMATCH {g.name} {xn} vs {yn} level {d}")
            need[xn] = max(need[xn], stab); need[yn] = max(need[yn], stab)
    print(f"{g.name}: done ({time.time()-t0:.0f}s)")
print(f"\n{cells} (pair, level) cells compared, {mism} mismatches")
print("budget from which each agent plays the idealised fixed point against every opponent in these games:")
for n in names: print(f"  {n:14s} {need[n]}")
print("ALL OK" if mism == 0 else "SOME FAILED")

"""Games with side payments: an action is (base action, transfer t in 0..T paid to the other player).
Payoffs: (u - t_row + t_col, v - t_col + t_row).  With transfers the Pareto frontier contains the whole segment
u + v = max joint payoff of width 2T, so the Nash bargaining solution and the equal-surplus (Shapley) split
coincide whenever T is large enough to reach it: NBS over a transferable-utility set IS the equal split."""
from rmodal import Game

def with_transfers(g, T):
    acts = ([f"{a}+{t}" if t else a for a in g.acts[0] for t in range(T + 1)],
            [f"{b}+{t}" if t else b for b in g.acts[1] for t in range(T + 1)])
    U = {}
    for i, a in enumerate(g.acts[0]):
        for ti in range(T + 1):
            for j, b in enumerate(g.acts[1]):
                for tj in range(T + 1):
                    u, v = g.U[(i, j)]
                    U[(i * (T + 1) + ti, j * (T + 1) + tj)] = (u - ti + tj, v - tj + ti)
    return Game(f"{g.name}+T{T}", acts, U)

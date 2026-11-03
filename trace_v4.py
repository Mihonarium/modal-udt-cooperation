from modal import *
from v4 import V4
from run import G
g = G("PD", (["C","D"],)*2, [[(2,2),(0,3)],[(3,0),(1,1)]])
ctx = Ctx(g, (0,0), (1,1))
X = V4("V4")
dl, d = X.program(g, 0, (X, None, 0), (None, X, 1), ctx)
print("V4 PD checks: 0: Box(C->oppC) & Box_1(not opp(Ex=D)=C) -> C ; 1: Box_1(D->oppC) -> D ; 2: Box(D->payoff>=1) -> D ; fallback D")
def tr(X, Y, L=6):
    progs = {}; todo = [(X, Y, 0), (Y, X, 1)]
    while todo:
        k = todo.pop()
        if k in progs: continue
        A, B, r = k; dl, d = A.program(g, r, k, (B, A, 1-r), ctx); progs[k] = (dl, d)
        for c, _ in dl:
            for v in vars_of(c):
                if v not in progs: todo.append(v)
    val, memo = [], {}
    print(f"== {X.name} (row) vs {Y.name}")
    for n in range(L):
        row = {}; val.append(row); fired = {}
        for k, (dl, d) in progs.items():
            act, f = d, "fallback"
            for i, (c, a) in enumerate(dl):
                if c.ev(val, n, memo): act, f = a, f"check{i}"; break
            row[k] = act; fired[k] = f
        print(f" L{n}: " + "  ".join(f"{k[0]} v {k[1]}={'CD'[row[k]]}({fired[k]})" for k in progs))
tr(X, Const(0, "CB")); tr(X, PrudentBot())

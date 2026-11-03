from modal import *
from v3 import V3
from run import G
g = G("PD", (["C","D"],)*2, [[(2,2),(0,3)],[(3,0),(1,1)]])
ctx = Ctx(g, (0,0), (1,1)); ctx.consts = {1: Const(1, "DB")}
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
        print(f" L{n}: " + "  ".join(f"{k[0]}v{k[1]}={'CD'[row[k]]}({fired[k]})" for k in progs))
for sub, kw in [("V3-A", dict(xform="PA+1")), ("V3-B", dict(order="exploit-last"))]:
    X = V3(sub, **kw)
    print(sub, "checks:", [("PA+1 " if (isinstance(c, Box) and c.k == 1) else "PA ") + "CD"[a] for c, a in X.program(g, 0, (X, None, 0), (None, X, 1), ctx)[0]])
    tr(X, PrudentBot()); tr(X, ctx.consts[1])

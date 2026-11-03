from modal import *
from run import G
g = G("PD", (["C","D"],)*2, [[(2,2),(0,3)],[(3,0),(1,1)]])
ctx = Ctx(g, (0,0), (1,1))
U = ModalUDT("UDT", default=1)
for opp in (PrudentBot(), FairBot()):
    # replicate play() but record which decision fired
    progs = {}; todo = [(U, opp, 0), (opp, U, 1)]
    while todo:
        k = todo.pop()
        if k in progs: continue
        A, B, r = k; dl, d = A.program(g, r, k, (B, A, 1-r), ctx); progs[k] = (dl, d)
        for c, _ in dl:
            for v in vars_of(c):
                if v not in progs: todo.append(v)
    val, memo = [], {}
    print(f"== UDT (row) vs {opp.name}; UDT checks: 0:(3,C)=□¬C 1:(3,D)=□(D→oppC) 2:(2,C)=□(C→oppC) 3:(2,D)=□¬D 4:(1,C)=□¬C 5:(1,D)=□(D→⊤)...")
    for n in range(7):
        row = {}; val.append(row); fired = {}
        for k, (dl, d) in progs.items():
            act, f = d, "default"
            for i, (c, a) in enumerate(dl):
                if c.ev(val, n, memo): act, f = a, i; break
            row[k] = act; fired[k] = f
        print(f" L{n}: " + "  ".join(f"{k[0]}v{k[1]}={'CD'[row[k]]}[{fired[k]}]" for k in progs))

"""The program-equilibrium environment, and the bot sources.

The environment does one thing: run a program's source in a fresh Python interpreter (separate process, isolated
mode, no bytecode cache, empty environment, working directory "/"), give it the opponent's source on stdin, with
a CPU-time and memory limit, and read back one action. Nothing is shared between the two players of a match.

make_bot(spec) builds a bot's complete source: its SPEC line plus its own copy of the prover in pe_bot.py.
"""
import os, resource, subprocess, sys, time

BODY = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pe_bot.py")).read()
CPU_LIMIT = 3600                 # seconds of CPU per program run
MEM_LIMIT = 5 * 2 ** 30          # bytes of address space per program run

def make_bot(spec, body=BODY):
    code = "SPEC = %r\n" % spec + body
    return "CODE = %r\nexec(CODE)\n" % code

def fairbot(k): return make_bot(f"C if prove(0, {idx(k)}, opp(self) == C)\nD otherwise")
def prudentbot(k):
    return make_bot(f"C if prove(0, {idx(k)}, opp(self) == C) and prove(1, {idx(k)}, opp(CONST_D) != C)\nD otherwise")
def v4bot(k, probe=1): return make_bot(f"V4 budget={idx(k)} probe={probe}")
CB, DB = 'print("C")\n', 'print("D")\n'
INF = "inf"
def idx(k): return "inf" if k == INF else str(k)

def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT, CPU_LIMIT + 5))
    resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT, MEM_LIMIT))

def run(src, opp_src):
    """Run program src on input opp_src. Returns (action or None, info dict)."""
    t = time.time()
    try:
        p = subprocess.run([sys.executable, "-I", "-B", "-c", src], input=opp_src, capture_output=True,
                           text=True, timeout=CPU_LIMIT * 1.5, cwd="/", env={"PATH": "/usr/bin:/bin"},
                           preexec_fn=_limits)
        out, rc, err = p.stdout.strip(), p.returncode, p.stderr[-500:]
    except subprocess.TimeoutExpired:
        out, rc, err = "", "timeout", ""
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    act = out if out in ("C", "D") else None
    return act, dict(returncode=rc, stderr=err, seconds=round(time.time() - t, 1), maxrss_children_kb=ru.ru_maxrss)

def outcome(act):
    """A run that produces no valid action counts as D (and is reported)."""
    return act if act is not None else "D"

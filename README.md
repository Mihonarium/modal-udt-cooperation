# Modal UDT and program equilibrium: can a payoff-reading agent cooperate like PrudentBot?

A small, exact study of agents that read each other's source code, in the framework of Bárász, Christiano,
Fallenstein, Herreshoff, LaVictoire and Yudkowsky, "Robust Cooperation in the Prisoner's Dilemma: Program
Equilibrium via Provability Logic" ([arXiv:1401.5577](https://arxiv.org/abs/1401.5577)).

The question: can an agent that takes the **payoff matrix as input** and searches outcomes from best to worst
("modal UDT") cooperate with FairBot, PrudentBot and itself, avoid exploitation by DefectBot, and work in general
two-player games?

## How the evaluation works

Agents are formulas of provability logic (GL): "play a if PA proves φ", where φ talks about the opponent's action.
Such agents have unique fixed points, and their joint play can be computed **exactly** by evaluating along the
Kripke chain of GL: level n "sees" all levels below it, `Box_k φ` (provability in PA+k) is true at level n iff φ is
true at every level m with k ≤ m < n. Every closed formula is eventually constant along the chain, and that value is
its truth value in the standard model. `modal.py` implements this; no proof search is needed.

Checks: `test_paper.py` reproduces the paper's outcomes (FairBot/PrudentBot/CooperateBot/DefectBot, PrudentBot vs
CooperateBot from PA+2, PrudentBot with a PA probe losing self-cooperation); `test_naive.py` checks the evaluator
against the literal definition on 5,880 pairings.

## Results

**Greedy modal UDT** (check "if I play a, I get at least u" for u from best to worst):
- Prisoner's Dilemma: cooperates with an identical copy; **defects against FairBot and PrudentBot**; exploits
  CooperateBot; defects against a copy that orders actions differently. Never gets less than its maxmin.
- Why it defects against PrudentBot: its first check, "if I defect I get the temptation payoff", passes vacuously
  at level 1 (it has never defected below level 1), so it defects once; PrudentBot and FairBot need its cooperation
  at every lower level, so they defect from then on (`trace_pb.py`).

**Version 3**, tiered checks (`v3.py`). Label each outcome (my payoff u, theirs v) with maxmins m_me, m_opp:
cooperative if u ≥ m_me, v ≥ m_opp and one is strictly better; exploitative if v < m_opp; neutral otherwise.
- V3-A (exploit checks in PA+1, interleaved by utility): fails; PA+1 checks are vacuous at levels 0 and 1, so the
  greedy defection fires even earlier.
- **V3-B** (all cooperative and neutral checks first, in PA, best u to worst; then exploitative checks in PA+1;
  checks below my maxmin dropped; fallback = maxmin action): cooperates with FairBot, PrudentBot and itself, and
  defects against DefectBot, in all 6 PD payoff sets tried. But in the PD its exploit check never runs, so it
  reduces to a FairBot variant and also cooperates with CooperateBot. That matches the paper's Thm 4.10: "Any modal
  agent X of rank 0 such that PA⊢[X(FB)=C] must also have PA⊢[X(CB)=C]." Exploiting CooperateBot needs a probe like
  PrudentBot's (how does the opponent play against DefectBot).
- Other games: Stag Hunt reaches (S,S); Chicken (Sw,Sw) among these agents, though they take advantage of FairBot
  and PrudentBot; **Battle of the Sexes and coordination games mis-coordinate** when two copies order equally good
  actions differently. Over 600 random 2x2/3x3 games, copies miss an outcome that is best for both players in 13% of
  the games that have one (V3-B), against 38% for greedy modal UDT.
- Never suckered: no version ever gets below its own maxmin (guaranteed by dropping checks below it).

**Version 4**, V3 plus a probe read off the payoffs (`v4.py`). It is rank 1: it asks how the opponent plays
against a third agent, which the paper's Thm 4.10 makes necessary for an agent that exploits CooperateBot.
- For each cooperative outcome o = (a, b) with my payoff u, let a_ex(b) be my best response to b, and Ex_b the
  constant agent that plays it.
- Cooperative check: PA proves "if I play a, I get at least u", AND PA+1 proves "the opponent does not play b
  against Ex_b". The probe is skipped when a is already a best response to b (nothing to exploit).
- Then exploitative checks, in PA+1: "if I play a, I get at least u". Then neutral checks, in PA.
- Checks below my maxmin are dropped; the fallback is the maxmin action.
- In the PD this is exactly PrudentBot's test: cooperate if PA proves my cooperation brings theirs, and PA+1
  proves they defect against DefectBot.

Results:
- **PD, all 6 payoff sets, both seats: V4 reproduces PrudentBot's whole row**: C,C with FairBot, PrudentBot,
  itself, a copy with a different action order, and V3-B; D,D with DefectBot and with greedy modal UDT; and it
  exploits CooperateBot (D,C), from PA+2 on, as PrudentBot does (`test_v4.py`, `trace_v4.txt`).
- The variants (probe in PA+2, exploit checks gated on a failed probe, exploit checks last) give the same PD row.
- Other games: Stag Hunt (S,S) with everyone; Chicken (Sw,Sw) with itself, V3-B and greedy UDT, while it takes
  advantage of FairBot and PrudentBot; **Battle of the Sexes and coordination games still mis-coordinate** with a
  copy that orders equally good actions differently (`v4_tables.txt`).
- 600 random 2x2/3x3 games (`sweep_v4.txt`): never below its own maxmin against any opponent (0 cases; guaranteed
  by the floor). Two copies miss an outcome that is best for both players in 22 of the 188 games that have one
  (12%), against 13% for V3-B and 38% for greedy modal UDT.

## What this does and does not settle

- In the unbounded modal setting, a payoff-reading agent can get FairBot-style cooperation in the PD if exploitative
  checks are tried last (V3-B), and PrudentBot's full behaviour if it also probes the opponent against the
  constant exploiter its payoffs define (V4). In the PD, V4 then behaves like PrudentBot.
- **Equilibrium selection is unsolved**: in games with several good outcomes, the result depends on how each agent
  orders them. A shared ordering (for example the Nash bargaining solution, with ties broken by something both can
  compute) is the natural next step; it is not tested here.
- **The bounded case is open**: Critch's bounded Löb ([arXiv:1602.04184](https://arxiv.org/abs/1602.04184)) covers
  FairBot-style agents; no bounded analysis of these payoff-reading agents was found.

Sources on modal UDT write-ups (Fallenstein, Slepnev, orthonormal) were seen only through summaries, not read directly.

## Files

- `modal.py`: exact evaluator, FairBot, PrudentBot, constant bots, greedy modal UDT.
- `v3.py`: Version 3 variants. `v4.py`: Version 4; `test_v4.py` asserts PrudentBot's PD row; `run_v4.py`:
  V4 tournament (`v4_tables.txt`, `sweep_v4.txt`, `v4_results.json`); `trace_v4.py` -> `trace_v4.txt`. `run.py`, `run_v3.py`, `sweep*.py`: tournaments; outputs in `*.txt`, `*.json`,
  `tables.md`. `trace*.py`: level-by-level traces. `NOTES.md`: working notes with corrections.

Run: `python3 test_paper.py && python3 test_v4.py && python3 run_v4.py` (Python 3, no dependencies).

# Modal UDT and program equilibrium: can a payoff-reading agent cooperate like PrudentBot?

A small, exact study of agents that read each other's source code, in the framework of Bárász, Christiano,
Fallenstein, Herreshoff, LaVictoire and Yudkowsky, "Robust Cooperation in the Prisoner's Dilemma: Program
Equilibrium via Provability Logic" ([arXiv:1401.5577](https://arxiv.org/abs/1401.5577)).

The question: can an agent that takes the **payoff matrix as input** and searches outcomes from best to worst
("modal UDT") cooperate with FairBot, PrudentBot and itself, avoid exploitation by DefectBot, and work in general
two-player games?

**Two kinds of agent in this repo.** Everything up to "What this does and does not settle" is about
IDEALISED agents: formulas of provability logic whose boxes mean unbounded provability in PA. They are
evaluated exactly (below); they are not programs and cannot be run. Runnable bounded bots, real programs that
read the opponent's source and search for proofs within a budget, are in the section "Bounded agents".

## How the evaluation works (idealised agents)

Agents are formulas of provability logic (GL): "play a if PA proves φ", where φ talks about the opponent's action.
Such agents have unique fixed points, and their joint play can be computed **exactly** by evaluating along the
Kripke chain of GL: level n "sees" all levels below it, `Box_k φ` (provability in PA+k) is true at level n iff φ is
true at every level m with k ≤ m < n. Every closed formula is eventually constant along the chain, and that value is
its truth value in the standard model. `modal.py` implements this; no proof search is needed.

Checks: `test_paper.py` reproduces the paper's outcomes (FairBot/PrudentBot/CooperateBot/DefectBot, PrudentBot vs
CooperateBot from PA+2, PrudentBot with a PA probe losing self-cooperation); `test_naive.py` checks the evaluator
against the literal definition on 5,880 pairings.

## Results (idealised agents)

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

## What this does and does not settle (idealised agents)

- In the unbounded modal setting, a payoff-reading agent can get FairBot-style cooperation in the PD if exploitative
  checks are tried last (V3-B), and PrudentBot's full behaviour if it also probes the opponent against the
  constant exploiter its payoffs define (V4). In the PD, V4 then behaves like PrudentBot.
- **Equilibrium selection is unsolved**: in games with several good outcomes, the result depends on how each agent
  orders them. A shared ordering (for example the Nash bargaining solution, with ties broken by something both can
  compute) is the natural next step; it is not tested here.
- The bounded case: see "Bounded agents" below (theory with PROVEN/ARGUED/OPEN labels, and runnable bots in a
  small exact proof system, which is not Peano Arithmetic).

Sources on modal UDT write-ups (Fallenstein, Slepnev, orthonormal) were seen only through summaries, not read directly.

## Bounded agents

> **Correction (2026-11-03): the tournament below breaks the program-equilibrium rules.** In program equilibrium
> each program receives only the opponent's source and returns an action. Here the bots instead call a primitive
> `prove(...)` supplied by `bounded.py`: the library builds one BPC system per match (`lang` canonicalises the pair
> of sources, `SYSTEMS` caches it), and both bots query that same environment-supplied object. That is an oracle
> outside the rules. The results below are kept, but they only show cooperation among bots that **share one
> prover supplied by the environment**; they do not show that self-contained programs cooperate.
> The rebuilt version that follows the rules is in "Self-contained bots" below.

Question: can FairBot, PrudentBot and V4 be written as real programs that search for proofs up to a budget k,
as in Critch, "Parametric Bounded Löb's Theorem and Robust Cooperation of Bounded Agents"
([arXiv:1602.04184](https://arxiv.org/abs/1602.04184), read directly), and do idealised agents cooperate with them?

**Short answer.**
- Idealised vs bounded: an idealised agent treats any bounded (always-halting) bot as the constant bot that plays
  the bot's actual moves (PROVEN, below). So idealised FairBot cooperates with FairBot_k exactly when FairBot_k
  cooperates with it, which by Critch's bounded Löb happens for every large enough k (ARGUED; the threshold is not
  computed by anyone). Idealised PrudentBot cooperates with a bounded bot iff the bot cooperates with it and defects
  against DefectBot.
- A faithful implementation (bots searching Peano Arithmetic proofs by length in characters) is not runnable:
  the Löbian cooperation proof is far longer than any exhaustive search can reach (ARGUED below). What runs here
  is a weaker but exact substitute: bots are real programs, read the opponent's source and search a small formal
  system completely up to a budget; the budget counts nested necessitations, not characters. Differences are
  listed under "How this differs from Critch".

### Theory

Notation: □φ "PA proves φ"; □_k φ "PA proves φ with a proof of at most k characters"; FB_k, PB_k, V4_k are
FairBot, PrudentBot and V4 with every "PA proves" replaced by "a proof of at most k characters is found".
Critch's Properties 1-4 (implication distribution with constant overhead, quantifier distribution with lg k
overhead, bounded necessitation and bounded inner necessitation with an expansion function E) are assumptions
about the proof system that he states with proof sketches only; everything ARGUED below inherits them.

1. **Bounded vs bounded (Critch's theorems).** PROVEN in arXiv:1602.04184 under Properties 1-4:
   - Thm 3 (parametric bounded Löb): if f is computable with f(k) ≻ E(O(lg k)) and
     ⊢ ∀k (□_{f(k)} p(k) → p(k)), then ⊢ ∀k > k̂, p(k) for some k̂.
   - FB_k vs FB_k cooperates for all k > k̂ (Sec. 6, p(k) = "FB_k(FB_k) = C").
   - Thm 4: if E(O(lg k)) ≺ k, f satisfies E(O(lg k)) ≺ f(k) ≺ k, and G(ℓ) > 6 f(2ℓ), then any two G-fair agents
     A_m, B_n (⊢ □_{m+G(len Opp)}[Opp(A_m) = C] → A_m(Opp) = C) cooperate for all m, n above a threshold r.
     Note the budget must grow with the opponent's code length (G); fixed budgets are not covered.
   - OPEN: the size of k̂ and r for any concrete proof system; behaviour below them (cooperation need not be
     monotone in k, since a different k is a different sentence).
   - PB_k is not G-fair (its cooperation also needs the probe). ARGUED: the probe "PA+1 proves X(DB) ≠ C" has a
     PA+1 proof of length c + O(lg j) for X = FB_j, PB_j, V4_j ("X(DB) = C would need a PA proof that DB cooperates;
     PA proves DB defects; PA is consistent"), so for budgets above that the probe holds outright and the
     Critch argument goes through with p = mutual cooperation. Not checked by anyone else.

2. **Idealised vs bounded.**
   - Collapse lemma, PROVEN (standard): if X always halts (every bounded proof searcher does), the sentence
     "X(Y) = a" is decided by PA: PA proves it when true (Σ1-completeness, the run is a finite computation) and
     proves its negation when false (the run halts with another action). PA is sound, so within any box,
     "X(Y) = a" can be replaced by ⊤ or ⊥ according to X's actual move. Hence an idealised agent plays against X
     exactly as against the constant bot that plays X's actual moves (against it and against any probe).
   - Consequences, PROVEN: idealised FB(X) = C iff X(FB) = C. Idealised PB(X) = C iff X(PB) = C and X(DB) = D
     (PA+1 proves "X(DB) = D" iff it is true). Idealised V4 vs X: the existing evaluator with X replaced by
     constants.
   - So everything hinges on what the bounded bot does against the idealised one. FB vs FB_k: let
     q_k := "FB_k(FB) = C". Then ⊢ q_k ↔ □_k □q_k. ARGUED: ⊢ ∀k (□_{f(k)} q_k → q_k) whenever
     E(f(k)) + O(lg k) < k eventually (from □_{f(k)} q_k: bounded inner necessitation gives □_{E f(k)}□_{f(k)} q_k;
     the uniform short proof of □_{f}φ → □φ and implication distribution give □_{E f(k)+O(lg k)} □q_k, which is
     q_k). Thm 3 then gives q_k for all k > k̂, and with it FB(FB_k) = C. Equivalently: idealised FB is G-fair for
     every G, so Thm 4's argument applies with an unbounded budget on its side. Cooperation for small k fails
     trivially (no proof that short exists): PROVEN. The same argument with the probe (item 1) covers idealised PB
     vs PB_k and idealised PB vs V4_k (ARGUED).
   - So the answer to "can idealised agents cooperate with bounded ones" is yes, for budgets above an unknown
     threshold; the idealised side is never the obstacle, because it simply mirrors.

3. **Payoff-reading agents (V4_k) and short spurious proofs.**
   - Floor, PROVEN (soundness of PA, PA+1): a check that fires is a real proof of "I play a → my payoff ≥ u" and
     the bot then plays a, so its payoff is ≥ u ≥ its maxmin; the fallback is the maxmin action. V4_k is never
     suckered, for every k.
   - Vacuous passes, PROVEN harmless: a check "⊢_k V4_k(X) = a → ..." can pass vacuously through a short proof of
     V4_k(X) ≠ a. But if it is the first check to pass, V4_k plays a, contradicting a sound proof; so a vacuous pass
     can only happen to a check after the one that fires, and never changes the action. (In the idealised
     Kripke evaluation the same thing shows up as greedy UDT's level-1 artefact.)
   - Order of checks in the PD, PROVEN: every check after the cooperative one (exploit in PA+1, neutral, fallback)
     plays D, so the order among them cannot matter; below its cooperation threshold V4_k simply defects through the
     trivially provable neutral check "D → payoff ≥ P".
   - Cooperation without Löb, ARGUED for PA (computed in BPC): V4's cooperative check is an implication, "if I
     cooperate, the opponent cooperates". Against FB_m, if V4_k cooperates then a proof of that fact of length about
     E(k) exists (bounded Σ1-completeness, as in Critch's Property 4). So when m exceeds that length, the implication
     has a short uniform proof and no Löbian fixed point is needed. The budgets must be ordered the right way: FairBot
     must out-budget V4.
   - New failure mode with several cooperative outcomes, ARGUED/OPEN: a lower-ranked cooperative check whose proof
     is shorter can fire at budgets where the better outcome's Löbian proof is not yet within reach, so equilibrium
     selection becomes budget dependent. Not tested here (PD only).

### Was a faithful implementation possible?

No, not for PA with proof length in characters. A FairBot_k that enumerates PA proofs of ≤ k symbols runs in
time |Σ|^k. The shortest proof of "FB_k(FB_k) = C" contains the diagonal (fixed-point) construction for the bots,
the Gödel encoding of the bounded provability predicate and Critch's argument; any written-out version is at least
thousands of symbols (ARGUED, rough estimate; no one has computed it). Exhaustive search stops at k ≈ 10-15,
where such bots would find no proof about another bot's behaviour (ARGUED) and so defect against everyone,
CooperateBot possibly included. Lean is not available here and was not installed; no existing bounded prover for this
setting was found.

### What was built (`bounded.py`)

- **Bots are programs.** A bot is source text, for example FairBot with budget 2:
  `C if prove(0, 2, opp(self) == C)` / `D otherwise`; PrudentBot adds `and prove(1, 2, opp(CONST_D) != C)`;
  V4 is `V4 budget=2 probe=1`, which reads the payoff matrix at run time and builds its checks as in `v4.py`.
  `bounded.act(game, X_source, Y_source, role)` runs bot X against bot Y and returns its action.
- **The formal system, BPC** (a "bounded provability calculus", one per match, built from the two sources):
  propositional formulas over action atoms [X|Y=a] ("program X outputs a against Y"), box atoms
  Box_n^t φ ("φ has a derivation of height ≤ n", t = 0 base theory, t = 1 base plus consistency, the analogue of
  PA+1) and Löb-shaped fixed points ψ ↔ (Box_g ψ → T), T a joint action of the match.
  Axioms: Unf (a bot's action is what its decision list returns, read off its source); FP (the fixed points);
  Mono, Incl, Four (Box_n ψ → Box_{n+1} Box_n ψ), FPBox/KFP (distribution through the fixed points), Ent (boxes are
  closed under propositional consequence of box-free contents), Sigma1 and UnfBox (a box-positive condition that
  holds is provable), and in theory 1, Con (the base system proves no contradiction).
  Rules: propositional consequence (free) and necessitation (height + 1). Height = number of nested
  necessitations; this is the budget k.
- **Genuine search, no answers added.** No axiom states any bot's output; Unf only says how a bot's output
  depends on what is provable. Each axiom is a true statement
  about the programs and the calculus; `bounded.audit` re-checks every axiom of every match system against the
  bots' actual outputs and the actual derivability relation, and the tournament audits all 400 systems. The
  fixed points are only definitions; cooperation, where it happens, is derived by the search from them (Löb's
  argument, found by the solver, not supplied).
- **Exact and complete for BPC.** With necessitation restricted to the finitely many formulas that occur in boxes,
  the set of derivable formulas at each height is finite; it is computed exactly with a small DPLL solver
  (propositional consequence) layered by height. So "budget k" means: every BPC proof of height ≤ k is
  considered.

### How this differs from Critch

1. Budget = necessitation height, not characters. Propositional reasoning is free. As a result the cooperation
   thresholds are tiny (the Löb argument needs one or two nested necessitations), whereas Critch's k̂ is the
   character length of a Löb proof in PA.
2. BPC is not arithmetic. It has no diagonal lemma, only the Löb-shaped fixed points for the joint actions of
   the match, and necessitation only for formulas that occur in boxes. Proofs outside that fragment do not exist
   in BPC, so a BPC bot is weaker than a PA bot with the same "budget" idea.
3. The facts PA would prove about provability (distribution, inner necessitation, Σ1-completeness, consistency of
   the base system for theory 1) are axioms here, at zero cost, because they are true of BPC; in PA they are
   theorems with length costs (Critch's E and c).
4. Program semantics is the Unf axiom: the system reads the decision list off the source. V4's payoff analysis is
   executed when unfolding, not proved.
5. Each match has its own system, generated by the two sources (probes against constant bots get their own
   sub-systems). A bot's "PA" is therefore the system of its current match.
6. Idealised PA agents cannot be placed inside BPC (their box means PA-provability). The "inf" budget bots below
   are unbounded BPC bots, which are computable because the system is finite; they reproduce the exact GL
   outcomes for FB, PB, V4, CB, DB (`test_bounded.py`).

### Tournament with a shared, environment-supplied prover (`run_bounded.py`, `bounded_tables.txt`, `bounded_results.json`)

These results are under the shared-prover setup described in the correction at the top of this section.

Row bot's action first. Budget = necessitation height in BPC; "inf" = unbounded BPC search (computable here).

```
Bounded PD tournament (row player's action first; 400 runs, 2464s wall). Budget = necessitation height in BPC.

          FB0   FB1   FB2   FB3   FB4 FBinf   PB0   PB1   PB2   PB3   PB4 PBinf  V4_0  V4_1  V4_2  V4_3  V4_4V4_inf    CB    DB
FB0        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    CC    DD
FB1        DD    CC    CC    CC    CC    CC    DD    DD    DD    DD    DD    DD    CC    DD    DD    DD    DD    DD    CC    DD
FB2        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FB3        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FB4        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FBinf      DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
PB0        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
PB1        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
PB2        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PB3        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PB4        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PBinf      DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_0       DD    CC    CC    CC    CC    CC    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
V4_1       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DC    DD
V4_2       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_3       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_4       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_inf     DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
CB         CC    CC    CC    CC    CC    CC    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CC    CD
DB         DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD

soundness audit: 0 false axioms over all 400 match systems
row bot (other than CB) cooperates while the opponent defects: never
```

What the table shows (all computed; thresholds are in BPC's height measure, not characters):
- Bounded vs bounded: FB_k and FB_m cooperate iff k, m ≥ 1 (the Löb argument needs one necessitation, see
  `trace_bounded.txt`). PrudentBot needs one more, for the probe: PB_k and PB_m cooperate iff k, m ≥ 2, and
  FB_k with PB_m iff both ≥ 2. V4_k and V4_m cooperate iff both ≥ 1 and one is ≥ 2; PB_k with V4_m iff k ≥ 2,
  m ≥ 1. Budget 0 cooperates only with CooperateBot (FairBot) or with FairBot_{≥1} (V4, next point).
- Budgets interact and smaller can be better. V4_0 cooperates with FB_1 but V4_1 does not. V4's check "if I
  cooperate, FairBot cooperates" is provable without Löb whenever FairBot's budget exceeds the height needed to
  verify V4's own cooperation (Sigma1). So FairBot must out-budget V4, which echoes Critch's requirement that the
  budget grow with the opponent (G-fairness).
- Idealised (unbounded BPC) vs bounded: FB_inf cooperates with FB_k (k ≥ 1), PB_k (k ≥ 2) and every V4_k;
  PB_inf with FB_k, PB_k (k ≥ 2) and V4_k (k ≥ 1); V4_inf with FB_k, PB_k (k ≥ 2) and V4_k (k ≥ 1). Below those
  budgets both sides defect. In every case the unbounded side just mirrors (collapse lemma).
- PrudentBot_k and V4_k exploit CooperateBot at every budget, including 0 (the probe fails because CooperateBot does
  cooperate with DefectBot). FairBot_k cooperates with it. Everyone defects with DefectBot.
- No proof-based bot ever played C against D (soundness). The audit found 0 false axioms in all 400 match systems,
  and the unbounded bots match the exact GL evaluator on all 25 pairings of FB, PB, V4, CB, DB.
- Not tested: other games, other payoff sets, larger budgets (K = 4 is the largest finite index in the language;
  everything is constant from k = 2 on).

Run: `python3 test_bounded.py && python3 run_bounded.py 10 && python3 trace_bounded.py` (Python 3, no
dependencies; the tournament takes about 2.7 CPU-hours (41 min wall with 4 workers) of CPU, run at low priority).

## Self-contained bots (program-equilibrium rules)

Rules (Kelvin, 2026-11-03): each bot receives only the opponent's source code; a bot may carry its own prover in
its own source, "but then that is all". The environment gives each program the other's source string and reads
back an action.

**What was built** (`pe_bot.py`, `pe_env.py`, `pe_run.py`, `pe_test.py`):
- **One source string per bot.** `pe_env.make_bot(spec)` produces `CODE = '<text>'` / `exec(CODE)`, where the text
  is a `SPEC = ...` line (the decision list, as before: FairBot, PrudentBot or `V4 budget=k probe=1`) followed by
  the whole of `pe_bot.py`: its own copy of BPC, the SAT solver, the height-layered search, the PD payoffs and the
  source analysis. Only the Python standard library is imported. A bot gets its own source by quining
  (`SELF = "CODE = %r\nexec(CODE)\n" % CODE`); nothing tells it its own source.
- **The environment** (`pe_env.run`) starts a fresh `python3 -I -B -c <source>` per program run, writes the
  opponent's source to stdin and reads one line (C or D) from stdout; empty environment, working directory `/`,
  limits 3600 s CPU and 5 GiB address space. A match is two such runs; self-play is two separate runs of the same
  source. No cache, file or object is shared between runs; each run builds its own match system from scratch.
- **Facts about the opponent come from reading its source.** The bot recognises exactly two forms:
  `print("C")` / `print("D")` (a constant program), and the form `CODE = '<SPEC line + text>'` / `exec(CODE)`
  whose text after the SPEC line is character-for-character its own prover. For the second form it writes the
  Unf axiom itself: the opponent's action is what the opponent's decision list returns, with each `prove(t, n, F)`
  read as derivability at height n in the same calculus (true because the code is identical and deterministic and
  builds the same match system; ARGUED, and checked by the audit below). Any other source is unknown: no Unf axiom,
  so nothing about its action is provable and the proof-based bots defect against it (`pe_test.py` checks this
  for FairBot_2 against FairBot_2's source with an extra trailing newline).
- **Atoms have no roles.** The old library tagged each atom with a seat (row/column). A program here receives only
  the opponent's source, so "X's action against Y" is one computation and one atom. In self-play "my action" and
  "the opponent's action" are therefore the same atom.
- **Audit (experimenter side, not seen by bots).** `pe_run.py` rebuilds every match system from the prover text
  and checks each axiom against the actual outputs of the separate runs and the actual derivability relation.

**Tournament** (`pe_tables.txt`, `pe_results.json`; COMPUTED). Identical embedded provers, same population and
budgets as before. Row bot's action first.

```
          FB0   FB1   FB2   FB3   FB4 FBinf   PB0   PB1   PB2   PB3   PB4 PBinf  V4_0  V4_1  V4_2  V4_3  V4_4V4_inf    CB    DB
FB0        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    CC    DD
FB1        DD    CC    CC    CC    CC    CC    DD    DD    DD    DD    DD    DD    CC    DD    DD    DD    DD    DD    CC    DD
FB2        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FB3        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FB4        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FBinf      DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
PB0        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
PB1        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
PB2        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PB3        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PB4        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PBinf      DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_0       DD    CC    CC    CC    CC    CC    DD    DD    DD    DD    DD    DD    CC    DD    DD    DD    DD    DD    DC    DD
V4_1       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_2       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_3       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_4       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_inf     DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
CB         CC    CC    CC    CC    CC    CC    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CC    CD
DB         DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
```

What it shows:
- COMPUTED: 398 of 400 cells are identical to the shared-prover table. The two differences are V4_0 and V4_1 in
  self-play, DD before and CC now. Reason: without roles, V4's cooperative check "if I play C the opponent plays C"
  is, against an exact copy of itself, the tautology [X|X=C] → [X|X=C], provable at height 0; with the old
  seat-tagged atoms it was a statement about two different atoms and needed the Löb argument. V4's probe (a copy of
  V4 would not cooperate with DefectBot) is already provable at budget 0 (as in V4_0 vs FB_1), so V4_0 and V4_1
  cooperate with themselves. This is a change of language (seat-free atoms, which the rules call for), not an effect
  of separating the provers. FairBot and PrudentBot self-play are unchanged.
- COMPUTED: soundness audit, 0 false axioms among 1,013,618 axioms of the 210 match systems; no proof-based bot
  played C against D; every one of the 420 runs produced a valid action within the limits (longest 55 s, peak
  memory under 55 MB); the two separate self-play runs agree for every bot.
- PROVEN (by construction): no prover object, cache or file is shared between the two players; the only thing
  that passes between them is the opponent's source string.
- So with identical embedded provers, the cooperation results of the shared-prover version survive the move to the
  program-equilibrium rules: the shared oracle was not doing the work, the shared prover CODE is.
- Cost: 420 runs in 936 s wall and the audit in 949 s wall, 4 worker processes, run at low priority.

**Not done yet (future work).** Bots whose provers differ: (a) the same logic with a trivially different but
equivalent implementation (renamed variables, reordered code), and (b) a genuinely different sound prover (other
axioms or another budget measure). The current bots recognise only their own prover text exactly, so in case (a)
they would treat the opponent as unknown and defect (the trailing-newline test above is one instance); cooperation
there needs a bot that proves the other prover equivalent to its own, or reasons about it by other means. Not
tested yet.

Run: `python3 -B pe_test.py && python3 -B pe_run.py 4` (Python 3, no dependencies; tests about 14 min, tournament
plus audit about 31 min wall with 4 workers).

## Files

- `modal.py`: exact evaluator, FairBot, PrudentBot, constant bots, greedy modal UDT.
- `v3.py`: Version 3 variants. `v4.py`: Version 4; `test_v4.py` asserts PrudentBot's PD row; `run_v4.py`:
  V4 tournament (`v4_tables.txt`, `sweep_v4.txt`, `v4_results.json`); `trace_v4.py` -> `trace_v4.txt`. `run.py`, `run_v3.py`, `sweep*.py`: tournaments; outputs in `*.txt`, `*.json`,
  `tables.md`. `trace*.py`: level-by-level traces. `NOTES.md`: working notes with corrections.

- `bounded.py`: runnable bounded bots and the calculus BPC (parser for bot sources, exact height-bounded
  derivability with a DPLL solver, soundness audit). `test_bounded.py`: unbounded bots vs the GL evaluator, audits,
  budget-0 and unexploitability checks. `run_bounded.py` -> `bounded_tables.txt`, `bounded_results.json`.
  `trace_bounded.py` -> `trace_bounded.txt` (height at which each fact becomes derivable).
- `pe_bot.py`: the body of a self-contained bot (prover, source analysis, decision); embedded in every bot source,
  never imported. `pe_env.py`: bot sources and the environment (one fresh interpreter per run). `pe_run.py` ->
  `pe_tables.txt`, `pe_results.json` (tournament and audit). `pe_test.py`: tests for the self-contained bots.

Run: `python3 test_paper.py && python3 test_v4.py && python3 run_v4.py` (Python 3, no dependencies).

## Version 5: outside randomness, a fair point read off the payoffs, and threats (`rmodal.py`, `v5.py`)

Added 2026-11-04 at Mikhail's request: can the agent take an outside source of randomness, read the
payoff matrix, exploit the opponent when it can, otherwise settle for a fair outcome, and otherwise give
in to threats without incentivising them ([Samin, "An approach to giving in to threats without
incentivizing them"](https://mishasamin-me.pages.dev/How_To_Give_In_To_Threats.pdf))?  Idealised agents
only (exact GL evaluation, as in the first part of this README); nothing bounded.

**Randomness** (`rmodal.py`).  Random inputs are free atoms, discretised: a public draw `r_pub`
(NPUB values, seen by both players; realises correlated outcomes such as "a coin decides who swerves"),
and per player a coarse private draw `r_c` (K values) and a fine private draw `r_f` (M values, the dial
for giving in with a probability).  An agent's action is a function of its own draws and r_pub; a key is
(agent, opponent, role, r_pub, r_c, r_f).  Conditions may talk about the opponent's keys at any draw
("PA proves the opponent plays b at every value of its private draw" is a statement about its policy,
which its source reveals), never condition an action on the opponent's realised private draw, and the
whole system of keys has one fixed point on the chain, evaluated exactly as before.  Expected payoffs
average the eventual actions over all draws.

**V5** (`v5.py`), for my key (r_pub, r_c, r_f):
- Fair point F = discretised Nash bargaining solution over the convex hull of the pure outcomes, with
  the pure maxmin values as the disagreement point: a mix of at most two pure outcomes, weight a
  multiple of 1/NPUB, realised by r_pub.  Both players compute the same F from the same matrix (this is
  the shared ordering the equilibrium-selection note above asked for).  Ties among payoff-equal outcomes
  go to the actions that leave the other player the least to gain by deviating.
- A (exploit): for each opponent action b whose best response a gives me more than my fair payoff,
  `Con_{k+4} and Box_k(the opponent plays b at every key against Const_a)` -> play a.  This is
  PrudentBot's probe turned around; the implication form "I play a -> they play b" is not used because
  it passes vacuously whenever I don't play a (the level-1 artefact of greedy modal UDT above).
- B (fair): `Box_0(I play F at all my keys -> the opponent plays F at all its keys)` -> play F(r_pub).
  FairBot's test aimed at F; Löb gives mutual F between copies, and with FairBot/PrudentBot aimed at F.
- C (threats): for each policy sigma the opponent could have at this r_pub (with K = 1: "x when
  r_f < j else y", which is what a stone, a FairBot or a V5 in tier C plays; with K > 1 a pure action
  per coarse draw), `Con_{k+3} and Box_k(opponent plays sigma)` -> respond to its distribution q:
  a* = my best response to q, v_give = the opponent's payoff under a*, a_r = the action minimising its
  payoff, v_ref its payoff then; if v_give <= v_F play a*; else give in (a*) when r_f < p*M and refuse
  (a_r) otherwise, p the largest multiple of 1/M strictly below (v_F - v_ref)/(v_give - v_ref), so the
  committed opponent gets strictly less than its fair payoff in expectation.  This is the paper's rule;
  with the paper's Chicken matrix it gives swerving with p just under 102/105.
- D: maxmin action.
- `Con_j = not Box_j(bottom)` is false at levels <= j of the chain, so a PA+k check can only fire after
  the box has been read over several levels ("patience"); without it a one-level transient in the
  opponent's play (its own fallback while it waits to read a constant bot) is mistaken for its policy, and
  copies in Battle of the Sexes exploited each other instead of meeting at F.  Tier A waits one level
  longer than tier C for the same reason.  Checks are stratified over k = 1..6 so that an opponent whose
  play settles only after a few levels (another V5 reading me) is still read.
- Tier C can take the agent below its own maxmin (it accepts a small probability of the refused
  outcome, as the paper intends); A, B and D cannot.

**Results** (COMPUTED; `test_v5.py`, `run_v5.py` -> `v5_tables.txt`, `sweep_v5.txt`, `v5_results.json`):
- PD (4 payoff sets): V5 reproduces PrudentBot's row: F = (C,C); C,C with a copy, FairBot and
  PrudentBot (both seats); D,C against CooperateBot; D,D against DefectBot.  With T + S > 2R (the
  10/3/1/0 set) the fair point is the 50/50 correlated alternation of (C,D)/(D,C), worth (5,5) > (3,3);
  copies play it, and defect against a FairBot that insists on (C,C).
- Chicken (paper's matrix): F = coin over (Sw,DS)/(DS,Sw), worth (2,2); copies get exactly that and
  never crash.  Against a stone that never swerves, V5 swerves with p = 0.95 (M = 20; the threshold
  is 0.971) and the stone gets -0.25 < 2 in expectation (5 if V5 always gave in).  Against a stone that
  always swerves, V5 never swerves (5).  Against a stone mixing 50/50 with its private draw at K = 4,
  V5 reads the mix and the stone gets -0.15 <= 2 (always swerving would give it 2.5).
- Ultimatum in normal form (offerer picks the offer, responder picks a threshold; a mix over thresholds
  is any monotone acceptance rule): F = 5/5, which copies play.  A stone offering 4 is accepted with
  p = 19/24 (threshold 5/6) and gets 4.75 < 5; a stone offering 1 with p = 13/24 (threshold 5/9) and gets
  4.88; an offer of 7 is accepted always.  A V5 that thinks 50/50 is fair accepts a committed offer of 49
  of 100 with p = 0.98 (the paper's number) and the offerer gets 49.98.  A V5 offerer that thinks 4 of 10
  is fair, against a V5 responder that thinks 5: they settle at 5/5 (the offerer reads the responder's
  probabilistic policy and its best response to it is 5).
- Named games: Stag Hunt (S,S); Battle of the Sexes, Coord and CoordRanked: copies meet at F (the coin
  in BoS and Coord); Matching Pennies: copies get (0,0).  V5 exploits FairBot-F and PrudentBot-F in
  both Chickens, through their fallback: a FairBot whose fallback is to swerve swerves against a stone
  that doesn't, and tier A reads that (same as V3-B/V4 above).
- 200 random 2x2/3x3 games: copies reach exactly the fair point in 200/200 (never below their maxmin),
  and miss an outcome best for both players in 0 of the 66 games that have one (V4: 12%, greedy modal
  UDT: 38%).  With FairBot-F: at F in 327/400 seats, V5 above F in the other 73 (FairBot's fallback was
  exploitable).  With PrudentBot-F: at F in 219/400, V5 above F in 85, V5 below F in 96: PrudentBot's
  probe treats V5's answer to a constant bot (which can be V5's F action, when that is its best response
  or its giving-in mix) as cooperating with a stone, and punishes it.
- Threatener sweep: every pure commitment of the opponent in both seats of every game (1048 commitments,
  67 of them threats, i.e. the committer would get more than its fair payoff if V5 gave in): the
  committer's expected payoff is <= its fair payoff in 1048/1048 (67/67 threats).  A commitment that is a
  function of the public draw is handled per r_pub by the same checks, so pure commitments cover public
  mixes; private mixes are read only at the coarse resolution K.  V5 ends below its own maxmin in 45 of
  the 67 threat cases (the price of giving in) and in none of the others.

**Not settled / caveats.**  The decision to give in is the paper's; whether "committer's expected payoff
<= fair" is the right unexploitability notion when the committer is itself a reader (two V5s with
different fair points) is only tested in one Ultimatum case.  Reading an opponent's policy costs
`#actions^2 * M` boxes per public draw (`read="pure"` reads only pure commitments); private mixes
finer than K are not read and fall to the maxmin floor, which a privately mixing threatener can use.
Zero-sum games get a pure maxmin fallback, not the mixed one.  The patience constants (3 for tier C, 4
for tier A) are what made the named games work; they are not derived.  Bounded (BPC) versions are
not built.

Run: `python3 test_v5.py` (about 30 s) and `python3 run_v5.py 100` (about 2.5 min); Python 3, no dependencies.

## Bounded V5 (`bounded_v5.py`, `test_bounded_v5.py`)

A runnable version of V5: a program given as a source line (`V5B fair=nbs budget=k npub=... m=...`) that
receives the opponent's source text and halts.  COMPUTED results match the idealised ones on the cases tried:
PD row (C,C with a copy of budget >= 1, D,C against CooperateBot, D,D against DefectBot and against a budget-0
copy), Chicken (copies at the coin, 0.95 swerving against the never-swerve stone which then gets -0.25, 5
against the always-swerve stone, -0.15 for a private 50/50 mixer), Ultimatum (copies 5/5; a stone offering 4
accepted with 19/24 and getting 4.75), copies at the fair point in 30/30 random 2x2 games.  About 25 s.

How it is bounded, and what it is not:
- Recognised opponents are STONEs (a policy table over the draws, i.e. a commitment, pure or mixed) and
  V5B spec lines.  Any other source is unknown and gets the maxmin action.
- Facts about a stone are read off its table; the opponent's play against a stone is obtained by running it
  against that stone (halts: a stone runs nothing).  So tiers A and C are execution, not proof search.
- The Löbian step (tier B between two V5B bots) is the exact bounded search of `bounded.py`: after checking
  by execution that neither side exploits the other and that both aim at the same fair point, the question
  "do we both play F" is FairBot_k vs FairBot_m in BPC with the bots' budgets; cooperation needs both >= 1.
  The reduction of the opponent's decision list to its FairBot branch is established by execution and by
  comparing specs, where the fully-formal bots above establish it through Unf axioms.
- Tier C is applied to stones only.  Against another V5B it is skipped (reading its policy against me would
  mean running it against me, which runs me against it, and so on), so two V5B bots with different fair
  points end at their maxmin actions: the idealised V5 reaches a settlement there through stratified PA+k
  checks, which have no bounded counterpart in this construction.  OPEN.

## Side payments (`sidepay.py`)

`with_transfers(g, T)` turns every action into (action, transfer 0..T paid to the other player).  With transfers the
Pareto frontier contains the segment u + v = max joint payoff, and the Nash bargaining solution over such a set is the
equal split of the surplus over the disagreement point, i.e. the two-player Shapley value: COMPUTED on 30 random 2x2
games the two fair points agree in 24/30 without transfers and 30/30 with transfers up to 5, and V5 copies reach the
fair point with transfers in 30/30 (payment included).  Example: in the game [[(10,0),(1,1)],[(1,1),(1,1)]] the fair
point without transfers is (1,1) (nothing else is above the maxmin values for both); with transfers up to 5 it is
(5,5): row plays A and pays 5, column plays A.  Without side payments the agent takes the best reachable point and
leaves the rest on the table, which is accepted.

## Policy search over a prior (`udt_pop.py`) — a contrast, not the agent

A UDT-style agent that keeps V5's probes (what it can prove about the opponent) but chooses the action in every case
by maximising its expected payoff over a prior population of opponent programs (stones, predictor-threateners that
commit iff committing provably pays against the agent's own response to a stone, private mixers, FairBot/PrudentBot
aimed at F, a copy of itself), with every match evaluated exactly as a fixed point and the copy running the same
candidate.  COMPUTED on Chicken (paper's matrix, M = 20): with only stones and FairBots in the prior it gives in fully;
with any appreciable weight on predictors or copies it recovers V5's rule exactly (swerve with p = 0.95 against a
committed non-swerver, the largest grid value that keeps committing unprofitable; against an unreadable opponent the
same 0.95/0.05 mix once unreadable predictors are in the prior); on the PD it recovers PrudentBot.  This is kept as a
contrast only: Mikhail's position (2026-11-04) is that the response to a commitment must not depend on the committer's
internals or on how many stones the prior has, because the number of stones is itself a function of how stones are
treated; an agent that optimises against a fixed prior gives in to stones once they are common enough, which is the
incentive to be avoided.  V5 therefore keeps the threat-resistant response for every committer.  Caveats of the
search: coordinate ascent from three starting tables (the maxmin start is a local trap in Chicken), the exploit probe
can be fooled by a predictor that gives in against a constant but commits against the agent, and the Ultimatum run was
not finished at the time of writing (`udt_pop_ult4.log`).

## Grounded bounded V5: arbitrary opponent programs (`grounded_v5.py`, `test_grounded_v5.py`)

The exact bounded V5 above gives the maxmin action to any program it cannot parse.  This third implementation
handles ARBITRARY halting programs by running them, with the regress of mutual simulation ended as in Oesterheld,
"Robust program equilibrium" (2019): with probability eps per decision the bot acts without simulating (it plays its
part of F), so nested simulation ends with probability 1 and costs a geometric series in 1 - eps.  Bots are Python
source text `act(me, opp, r_pub, rng, game)`; a bot may `run` another source; runs burn fuel and the top-level run has
a wall-clock limit, so a program that loops or crashes is the only thing that still gets maxmin.  Commitment tables
are read exactly as before; probes against constant agents (which do not recurse) are sampled 60 times at every public
draw; the one recursive step is a single sample of the opponent against me; the give-in probability is set against
the committer's expectation over ALL public draws (a program committed to one action collects the coin's fair outcome
at the draws where that action is its part of F, so the probability elsewhere must be lower: 0.90 in Chicken rather
than 0.95).  COMPUTED (Monte Carlo over random tapes, eps = 0.05, 580 s):
- PD: copies C,C (3, 3); D against CooperateBot and DefectBot; C,C with an eps-grounded FairBot written in different
  code; against a program that never halts, or crashes, D except for the eps grounding.
- Chicken: copies play the coin with about 1% crashes from independent sample chains disagreeing, expected (0.95,
  1.01) against the ideal (2, 2); the committed non-swerver gets 1.06 < 2 and is swerved against 96% of the time; the
  always-swerver is taken for 5; a private 50/50 mixer (a table) gets -0.83.
- Ultimatum: copies 5/5; a stone offering 4 is accepted ~0.8 of the time and gets 4.89 < 5; an offerer that thinks 4
  is fair against a responder that thinks 5 settles at (3.39, 3.01), where the idealised pair reach (5, 5) and the
  exact bounded pair (0, 0).
- Random 2x2 games: copies within 0.5 of the fair point in 12/12.
Costs: sampling noise (the 1% crash rate; nothing like it in the exact versions), and time (seconds per decision in
the Ultimatum).  Not done: a proof-based treatment of foreign provers; the grounded bot trusts execution instead.

## Correction (2026-11-04, evening): the exploit probe, and the "different fair points" result

Mikhail asked two things.  (1) In Chicken, does V5 go Straight against an agent that swerves iff its opponent is
provably committed to Straight?  (2) Does V5 test the opponent against V5's own code, or only against code that
behaves like it?

(1) COMPUTED, `SIC(k, default)` = swerve iff PA+k proves the opponent plays Straight at every key against me, else
`default`.  Before the fix V5 took 5 from SIC with default Swerve at every k and from SIC with default Straight at
k = 7, but CRASHED (-100, -100) against SIC with default Straight checking in PA+0 or PA+1: V5's own Straight is only
provable in PA+k (its exploit check is guarded by Con(PA+k+4) so it cannot fire vacuously), so a weak-theory checker
does not see the commitment and goes Straight, while V5's probe ("it swerves against a constant Straight") had read it
as a pushover.  Swerving against a stone is not swerving against an agent.  Fix: tier A now requires BOTH
`Box_k(opponent plays b against Const_a)` AND `Box_k(opponent plays b against me)`.  After the fix: 5 against every SIC
with default Swerve and against SIC(PA+7, Straight); against SIC(PA+0 or PA+1, Straight) V5 reads it as committed to
Straight and gives in with p = 0.90 (M = 10), SIC gets -5.5 < 2, no crash.  Side effect, all for the better: in Chicken
V5 no longer takes advantage of FairBot-F and PrudentBot-F (they swerve against the constant but play F against V5),
both seats now (2, 2); in the random games FairBot-F reaches F in 358/400 seats (was 327) and PrudentBot-F in 243/400
(was 219); everything else in `run_v5.py` is unchanged (200/200, 0/66, 1048/1048, 67/67).  The grounded program got the
same conjunct (its probes come first because they do not recurse; the sample against me confirms).

(2) Yes.  Tier B is `Box(I play F at all my keys -> the opponent plays F at all ITS KEYS AGAINST ME)`: the keys are
(opponent, me, role, draws), the opponent's play against this agent, never against a proxy.  In the modal setting no
opponent can distinguish V5 from PrudentBot in the PD, because they play identically against every probe; in the
grounded program the source string is the identity, and COMPUTED: a program that cooperates with everyone except
V5G's source (and commitment tables, so the probe says nothing) is defected against (D 0.92, the rest the eps
grounding); a program that cooperates only with V5G's source gets C,C.

The "two idealised V5s with different fair points settle at 5/5" line in the V5 section above was an ARTEFACT.  The
pair has no fixed point: offer 4 -> the responder accepts with 9/12 -> offering 5 (5) now beats offering 4 (4.5) ->
facing mostly 5s the responder's best reply is to accept everything (4.75 > 3.75) -> offering 4 (6) beats 5 again.
The stratified readings cycle through these and the chain freezes at whichever point the last readable stratum lands
on (before the fix (o5, t5); after it (o4, t5), i.e. (0, 0); kmax = 8, 12, 16 all freeze at (0, 0) with growing
stabilisation level).  The right statement is the paper's: with different notions of fairness, one side's response
to the OTHER'S COMMITMENT is well defined (a stone offering 49 of 100 is accepted 98%), while two reactive readers do
not converge within one game.  The grounded program's (3.39, 3.01) for that pair is a time average over the same cycle.
`test_v5.py` now reports that case instead of asserting a settlement.

### Grounded V5, revised numbers (after the exploit-check fix)

Two things changed.  (a) Monte Carlo with a -100 outcome is noisy (the committed non-swerver's measured payoff moved
from 1.06 to 2.38 between 200 and 400 samples); against commitment tables the bot draws at most once and never
grounds, so `exact_vs_table` now enumerates that draw and gives exact figures: non-swerver -0.25 (swerve 0.95
overall: 1.0 where the coin already says so, 0.90 elsewhere), always-swerver -1 (taken for 5), private 50/50 mixer
-0.15, Ultimatum stone offering 4 accepted 19/24 and getting 4.75, offering 1 accepted 13/24 and getting 4.875:
identical to the idealised agent.  (b) With eps = 0.05 the sampled reading "opponent committed to Swerve ->
Straight" amplifies through the opponent's 0.9 give-in into a 10%-plus crash rate between copies (an earlier
low-crash run was a lucky draw; the fuel limit had been acting as a grounding to maxmin).  With eps = 0.1 copies play
the coin with no crash in 200 samples, (2, 2); eps = 0.2 and 0.3 the same.  Default is now eps = 0.1.  Against an
opponent whose own play is a noisy function of one sample of me (swerve iff a single sample of the opponent is
Straight, else Straight, grounded 5% to Straight) the sampling noise still compounds and both lose about -10; the
idealised agent handles that opponent exactly.

## Being a rock for rock-givers (2026-11-04, late)

Mikhail: "if we see that an opponent swerves against a Straight rock, it is because they proved the rock goes
Straight; we can search for a proof that if we go Straight the opponent swerves, and go Straight if we find one; an
opponent that searches for proofs of the other going Straight and swerves if it finds one is exploitable and will find
this proof by Löb."  And: "for opponents that give in to rocks, UDT can be effectively a rock."

Right in the standard model: with A = "I go Straight" and B = "they swerve", an agent with A <-> Box(A -> B) against
one with B <-> Box(A) gets, by Löb, PA |- A -> B, hence A and B, and the Straight is PA-provable.  COMPUTED (`L` in the
scratch script, = V5 with that check first, unguarded, Box_0): in Chicken it takes 5 from the commitment checker
reasoning in PA (where V5 gives in and gets -10.9), takes 5 from FairBot-F, meets a copy at the coin, and answers the
committed non-swerver as V5 does.  The cost is on the chain: Box_0(A -> B) is vacuously true at any level where the
agent has not yet gone Straight, so the check fires once against EVERYONE at the first or second level, and a
reciprocator whose condition is Box(opponent plays F), FairBot or PrudentBot, never forgives that: in the PD the
Löb-form agent gets D,D with FairBot and with PrudentBot (1, 1 instead of 3, 3), exactly greedy modal UDT's failure at
the top of this README.  Copies forgive each other because V5's reciprocation check is an implication and is vacuous
at levels where the copy was not playing F.

So the two facts are one fact.  Being a rock in plain PA means playing the rock's action from level 0, at first sight
against everyone, which is what breaks Löb cooperation with an unforgiving reciprocator in some other game.  PrudentBot
sits at the same boundary (its defection against CooperateBot is PA+2-provable, Barasz et al.).  The claim holds for
every rock-giver whose reading theory is at least as strong as the one our commitment is provable in, and V5 is such a
rock for all of them.  How weak a reader that is depends only on the patience constants: COMPUTED, against "swerve iff
PA+k proves the opponent goes Straight, else Straight", V5 with patience 3 is a rock for k >= 5, with patience 1 for
k >= 3, with patience 0 for k >= 2 (PrudentBot's level), and gives in (-10.9 for V5, -5.5 for the checker, below its
fair 2) for smaller k.  Patience had been introduced to stop a copy's one-level fallback against a constant from being
read as its policy; the "against me" conjunct in tier A now does that job, and with patience 0 every named-game and
random-game result is unchanged (`test_v5.py` ALL OK; `run_v5.py`: 200/200, 0/66, FairBot-F 358/400, PrudentBot-F
243/400, 1048/1048, 67/67).  Default patience is now 0: V5 is a rock for any commitment checker reasoning in PA+2 or
stronger, and is read as "not committed" only by checkers weaker than it takes to tell a reciprocator from a pushover.

## Correction and the level-0 rock (2026-11-05)

Mikhail: "we only defect against FairBot if they cooperate with us given our defection; we should never end up in
D,D where C,C is achievable."  Right about the first half: COMPUTED, the pure Löb-form agent "D iff Box(D -> opp C)"
against FairBot ends at C,D (0, 5), i.e. the check never fires in the limit (the earlier D,D came from V5's later
tiers reading FairBot's D as a commitment).  The D comes from FairBot's side: FairBot cooperates iff PA proves we
cooperate, and with the Löb-form check placed first "we cooperate" includes "PA does not prove D -> C", a
non-provability that PA cannot establish (not-Box X implies Con).  So FairBot cannot verify us and defects.  On the
chain the same fact is: a box-only condition is vacuously true at level 0, so the agent defects at level 0, and
FairBot's Box(we C) is false from level 1 on.  This is why PrudentBot's exploit test is a positive PA+1 conjunct
inside its cooperation condition rather than a prior check whose non-firing would have to be proved.

The general shape.  A PA-provable commitment is true at every level of the chain, so being a rock a PA-reasoner can
see means playing the rock's action at level 0, before anything is known about the opponent; being a PA-verifiable
cooperator means playing fair at level 0.  In one game these conflict; across games they need not, so the choice is
per game.  Mikhail's point that Chicken differs from the PD is exactly this: in Chicken a Straight rock is answered by
swerving by everyone who responds to first-order incentives, and a reciprocator whose fallback is Swerve loses
nothing to it, whereas in the PD a Defect rock gets Defect from every reciprocator.

V5R (`v5.py`): V5 with an unguarded tier A (fires at level 0, a PA-provable rock) in games that pass a gate computed
from the matrix alone, the same way the fair point is: (i) rock-safe for both seats, meaning the exploit action
against the opponent's maxmin action (a reciprocator's natural fallback) pays at least the fair payoff; (ii) not
constant-sum; (iii) copies of the rock agent still reach the fair point in this game (one self-play evaluation of
the matrix).  COMPUTED: the gate passes Chicken and Chicken-mild, fails the PDs, Stag Hunt, BoS, the coordination
games and Matching Pennies (looser gates broke copies in BoS, asymmetric, and in Matching Pennies, zero-sum), and
passes 2 of 200 random games.  In Chicken (paper's matrix) V5R vs: copy (2, 2); FairBot-F and PrudentBot-F (fallback
Swerve) 5 (V5: 2, 2); "swerve iff PA proves the opponent goes Straight, else Straight" 5 (V5: -10.9); the same in
PA+1, 5 (V5: -10.9); "swerve iff PA proves it, else Swerve" 5; rock Straight: give in 0.9, (-10.9, -5.5), unchanged;
rock Swerve 5; stubborn FairBot-F (plays F iff the opponent provably plays F, else Straight): V5R is read as a
non-cooperator, it goes Straight, V5R gives in 0.9: (-10.9, -5.5) where V5 got (2, 2).  That last opponent is the whole
cost, and it is a threatener against non-verifiable agents ("be provably fair or I go Straight"), which V5R answers as
it answers any commitment (the threatener ends below its fair 2).  Over all gated games (4), the commitment sweep
holds (18/18) and V5R ends below fair against a stubborn reciprocator in 6/18 cells.  Random games: copies at F
200/200 for both; against FairBot-F/PrudentBot-F in both seats V5R is better in 4 of 800 cells and worse in 0.
V5R is now the default in `test_v5.py` and `run_v5.py` (the Chicken rows against FB-F/PB-F in `v5_tables.txt` change
from (2, 2) to (5, -1); everything else is unchanged).  The grounded program does not need the gate: it samples the
opponent's action against its own source, so it is a rock to anyone who gives in to rocks by construction.

## V6: no exploit tier (2026-11-05, evening) — now the default

Mikhail: can we boundedly look for proofs of D -> C, fail, then cooperate, with FairBot knowing we will fail?  And:
"we cannot galaxy-brain ourselves into trying to exploit other agents in complicated ways."

COMPUTED in the bounded calculus (`bounded.py`, BPC): a bot that first searches (theory 0 or 1, budget 1 or 2) for
"if I defect the opponent cooperates" and otherwise plays FairBot_2 gets D,D with FairBot at budgets 1, 3 and inf,
with a FairBot reasoning in theory 1, with PrudentBot_2, and with a copy of itself; only CooperateBot is exploited.
The V5-shaped guarded form (exploit iff theory 1 is consistent about the match and PA proves the opponent cooperates
with DefectBot and with me) does no better: D,D with all of them.  The calculus has no rule turning "no derivation
found at height n" into a derivable negated box, and establishing non-firing of a guarded check needs reasoning about
nested boxes it does not have.  So in a weak bounded prover ANY exploit check placed before the cooperation condition
makes the bot unverifiable, whatever its guard.  (The exact bounded V5 escaped this only by replacing proof search
with execution.)  PrudentBot's shape is verifiable there because it has no prior exploit tier: "defects against
DefectBot" is a positive PA+1 conjunct of the cooperation condition.  The answer to the question is therefore: a
bounded FairBot knows we will fail only when our cooperation is a positive provability claim, never when it rests on
our own search having failed.

V6 (`v6.py`) takes the shape: B' = Box_0(I play F -> opponent plays F) and, for each opponent action b exploitable
for more than u_F, Box_2(the opponent does not play b at every key against Const_{best response to b}) -> play F;
C = V5's commitment tier (consistency-guarded, stratified); D' = against an unreadable opponent, the threat-resistant
response (treat it as committed to the action it would profit most from committing to against a best-responder, and
answer with C's rule) rather than maxmin.  No tier A: a pushover is a committed opponent and C best-responds to it.
The probe reads in PA+2 rather than PA+1: at level 1 an opponent facing the rock has not yet read it (its own C tier
first fires at level 2) and plays its default, which in 23 of 200 random games coincided with b and broke copies.

COMPUTED (`test_v5.py` ALL OK; `run_v5.py`): PD row as PrudentBot (D against CooperateBot through C); Chicken copies at
the coin; FairBot-F and PrudentBot-F taken for 5 in Chicken (they give in to the Straight rock, so B' refuses them
and C answers their Swerve fallback), which is "a rock for those who give in to rocks" without any rock tier; the
stubborn reciprocator (fair iff provably fair, else Straight) now gets (2, 2) because V6 is verifiable to it (V5R:
-10.9); "swerve iff PA proves Straight, else Straight" is still given in to (-10.9; V5R wins that one at the cost of
the stubborn reciprocator; it is kept as the alternative); Ultimatum 5/5, 19/24, 13/24 as before.  Random games:
copies at F 200/200, miss a both-best outcome 0/66, commitments 1048/1048 (threats 67/67), FairBot-F at F in 340/400
seats and ABOVE F (exploited through its fallback) in the rest where V5 was at F.  New sweep: unreadable private
mixers (1/2 and 9/10 on each action, both seats, every game, 2096 cases): the mixer's expected payoff is at most its
fair payoff in 2094/2096 (V5's maxmin default let a 50/50 Chicken mixer collect 2.5 > 2; V6 gives it -2.8).  The two
exceptions are mixes that beat D's single-commitment response by 0.2 and 0.05; a fully mix-proof default would be a
small LP over my actions and is not built.

### V6 with the level-0 rock in Chicken (2026-11-07) — default

Mikhail: against "Swerve iff PA proves my opponent goes Straight at every key against me; otherwise Straight" we
should go Straight.  A PA-provable Straight is true at level 0 of the chain, where nothing is known about anyone, so
it has to be the FIRST condition of the decision list, passing vacuously there; the Löb-form check does exactly
that ("if provably my Straight makes them swerve, go Straight"), and the only reason not to have it everywhere is
the PD, where the same level-0 seed is a Defect that FairBot never forgives.  So V6 now carries it first in games
that pass the rock gate and nowhere else:  Box_0(opponent plays b at every key against Const_a) and
Box_0(opponent plays b at every key against me) -> a, for the most profitable exploitable (a, b).  COMPUTED (Chicken,
paper's matrix): the PA-level non-rock punisher now swerves, (5, -1), was (-10.9, -5.5); everything else in the
Chicken table is as before, except the PA-level reciprocator whose fallback is Straight, which reads the rock as a
non-cooperator and goes Straight: V6 answers it as a commitment, (-10.9, -5.5), was (2, 2).  Those two opponents are
mirror images ("be provably a rock or I crash" / "be provably fair or I crash", both reading in PA) and one level-0
action can serve only one of them; Mikhail chose the rock.  The rock is a convention: a rock copy against a non-rock
copy gets (-0.4, -0.1) in Chicken.  Full sweep unchanged: `test_v5.py` ALL OK; copies at F 200/200, miss a both-best
outcome 0/66, FairBot-F at F 340/400 and above F elsewhere, commitments 1048/1048 (threats 67/67), unreadable mixers
2094/2096.

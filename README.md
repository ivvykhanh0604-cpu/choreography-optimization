# Graph Theory and the Hungarian Algorithm for Group Choreography

A small independent project exploring whether group-dance formation changes can be modeled as an assignment problem, and what happens when a mathematically efficient solution conflicts with actual choreographic intent.

I used selected formation changes from ONHIT's cover of ALLDAYPROJECT'S **"FAMOUS"** routine, represented dancer positions on a 2D coordinate grid using Formi Studio, and compared the original choreography with assignments produced by the Hungarian algorithm. I then extended the model with choreographic constraints such as preserving the focal member (center), screening for crossing movement paths (potential collision), and keeping specific dancers close to one another (relational constraint).

The project began with a simple question:
> **If the target formation stays the same, can dancers be reassigned to reduce total movement?**
The more interesting question eventually became:
> **How much of an apparently "inefficient" formation change is actually explained by artistic constraints that a distance-only model cannot see?**
---
## Mathematical framework

I model each formation change as a **weighted bipartite graph**.
For one transition, there are two vertex sets:
- \(D = \{d_1, d_2, \ldots, d_n\}\): dancers at their current positions
- \(S = \{s_1, s_2, \ldots, s_n\}\): target slots in the next formation

Every dancer can, in principle, be assigned to every target slot, so the basic model is a complete bipartite graph \(K_{n,n}\). Each edge has a cost equal to the Euclidean distance between a dancer and a target slot:
\[
c_{ij}
=
\sqrt{(x_i-x_j)^2+(y_i-y_j)^2}
\]

The assignment problem is then:
\[
\min \sum_{i=1}^{n}\sum_{j=1}^{n} c_{ij}x_{ij}
\]
subject to
\[
\sum_j x_{ij}=1
\qquad\text{for every dancer }i
\]
and
\[
\sum_i x_{ij}=1
\qquad\text{for every target slot }j.
\]

Here, \(x_{ij}=1\) means dancer \(i\) is assigned to target slot \(j\). I use SciPy's implementation of the **Hungarian algorithm** (`linear_sum_assignment`) to solve this minimum-cost assignment problem. Unlike brute-force enumeration of all \(n!\) assignments, the Hungarian algorithm solves the linear assignment problem in polynomial time.

The complete derivation, manual cost-matrix work, algorithm comparison, and longer discussion of assumptions are included in the [full project report](project_report.pdf).

## From mathematical optimum to choreographic constraints
A minimum-distance assignment is not automatically a good choreography. The first Hungarian results made this obvious. In some transitions, large distance reductions were achieved only by swapping performers into one another's intended roles. That led me to add several layers of constraints.

### 1. Focal-member preservation
Some formations are visually organized around a particular performer. Reassigning another dancer to that slot may reduce distance while destroying the intended focus. The model therefore supports both:
- a **soft focus penalty**, which makes taking the focal member's slot more expensive; and
- a **hard focus constraint**, which requires the focal member to keep that slot.

### 2. Movement-path crossing screening
Each dancer's movement is approximated as a straight-line segment between their starting and target coordinates. The program checks pairs of paths for geometric intersections. This is treated only as a **potential crossing risk**, not as proof of a real collision, because timing, body dimensions, and curved movement paths are not modeled.

### 3. Pair-distance constraints
Some choreographic relationships are relational rather than positional. For example, in the second test sequence, dancers W and Y are required to remain close to one another. Instead of forcing either dancer into one exact coordinate, the solver can reject assignments where their final separation exceeds a specified threshold.

### Why exhaustive search appears in part of the code
The Hungarian algorithm works when total cost is a sum of independent dancer-to-slot costs. Constraints such as
- "do these two movement paths cross?", or
- "do W and Y finish within 3 units of one another?"
depend on **pairs of assignments** rather than one dancer-slot edge alone.

For these small five-member examples, I therefore enumerate the \(5! = 120\) possible assignments when evaluating those constraints. This is practical at this scale, although it would not be an efficient approach for much larger groups.

## Experiments

I first developed the framework on formations **11–16**, giving five consecutive transitions. I then performed a **within-routine generalization test** on a previously unused section, formations **45–50**. The same analysis functions were reused without rewriting the optimization logic; only the formation coordinates and choreography-specific constraints changed.

The second sequence also introduced a new relational rule: W and Y must remain within 3 coordinate units in Formation 46. The unconstrained optimum already satisfied this rule, so the constraint was non-binding in that transition.

## Results
### Sequence 1: formations 11–16

| Transition | Original distance | Hungarian minimum | Choreography-constrained |
|---|---:|---:|---:|
| 11 → 12 | 42.20 | 42.14 | 42.20 |
| 12 → 13 | 24.62 | 12.65 | 24.37 |
| 13 → 14 | 9.22 | 9.22 | 9.22 |
| 14 → 15 | 40.27 | 34.41 | 38.44 |
| 15 → 16 | 15.21 | 15.21 | 15.21 |

The largest unconstrained improvement occurred in **12 → 13**, where total movement fell from 24.62 to 12.65 units, a reduction of about **48.6%**. However, that solution reassigned the focal role. Once T was required to retain the intended focal slot, the best distance became **24.37**, only about **1.0% below the original choreography**.

A similar effect appeared in **14 → 15**:
- original: 40.27
- pure Hungarian: 34.41
- focus-preserving: 38.44
This was one of the main findings of the project: some apparent geometric inefficiency was not simply "bad routing"; it reflected choreographic role constraints that the original distance-only objective could not represent.

The crossing analysis produced another interesting finding. Under the pure Hungarian assignment, all five transitions were crossing-free in the straight-line model. Once the focal member was fixed, formations 11 → 12 and 12 → 13 contained a crossing, and exhaustive search showed that **no completely crossing-free assignment existed while preserving that focal slot**. In other words, increasing a collision penalty could not solve those cases because the feasible assignment space itself contained no zero-crossing solution.

### Sequence 2: formations 45–50
| Transition | Original distance | Hungarian minimum | With relational constraint |
|---|---:|---:|---:|
| 45 → 46 | 24.24 | 21.85 | 21.85 |
| 46 → 47 | 15.42 | 14.22 | 14.22 |
| 47 → 48 | 11.00 | 11.00 | 11.00 |
| 48 → 49 | 12.00 | 12.00 | 12.00 |
| 49 → 50 | 6.00 | 6.00 | 6.00 |

The solver reduced movement by about **9.9%** for 45 → 46 and **7.8%** for 46 → 47. The remaining transitions were already minimum-distance assignments. This was useful for a different reason: optimization did **not** automatically produce improvements everywhere. In several transitions, the original choreography was already geometrically optimal under the model.

## What I learned
I originally expected the project to be mainly about using an optimization algorithm to find "better" dancer paths. It became more interesting when that assumptions started failing because a mathematically optimal assignment can be choreographically poor: Large numerical improvements may come from exchanging visual roles, breaking performer relationships, or creating movement patterns that would not make sense on stage.
The project therefore shifted from the simple exploration of the question:
> **"Can I minimize movement?"**
to:
> **"What information has to be added before a mathematical optimum becomes choreographically meaningful?"**
The full project report also explores **sequence continuity**. Optimizing one transition in isolation could place dancers badly for the next formation, so a local improvement could make a longer sequence worse. That experiment made the distinction between *local* and *sequence/global-level* optimization especially clear.

## Limitations
This is an exploratory mathematical model rather than an automated choreography system.
- Formation coordinates were estimated manually from the routine.
- Euclidean distance assumes straight-line movement and does not capture curved or stylized trajectories.
- Distance is treated as a proxy for movement cost; speed, direction, fatigue, and individual physical differences are ignored.
- A geometric path intersection is only a potential collision indicator because the model does not include timing.
- Most target coordinates remain fixed, whereas a real choreographer can continuously adjust the entire formation. I kept most target coordinates fixed deliberately to isolate the dancer-to-slot assignment problem. Allowing all positions to vary would turn the task into a much larger continuous formation-design problem and would require additional aesthetic and spatial constraints to prevent mathematically efficient but choreographically meaningless solutions. Fixing the target geometry also makes the comparison with the original choreography fairer, because any reduction in movement can be attributed to reassignment rather than redesign of the formation.
- The constrained search enumerates permutations and therefore scales factorially; it is practical here because the tested group has five dancers.

For those reasons, the model should be interpreted as a way to **analyze trade-offs**, not as a claim that mathematical optimization can replace choreographic judgment.

## Running the code
### Requirements
- Python 3
- NumPy
- SciPy
Install the dependencies:
```bash
pip install numpy scipy
```

Run:
```bash
python choreo_solver.py
```

The script prints a summary for both tested formation sequences, including:
- original movement distance;
- Hungarian minimum distance;
- detected straight-line path crossings;
- constrained movement distance;
- constrained crossing count; and
- whether a fully crossing-free constrained assignment exists.

## Repository structure

```text
.
├── choreo_solver.py      # reusable optimization and constraint logic
├── project_report.pdf    # full mathematical development and project notes
└── README.md
```

## Project status

This is a finished exploratory version of the project.

Possible future extensions will address three of the more straightforward limitations of the current model. First, the factorial exhaustive search used for choreographic constraints can be replaced with a more scalable constraint-optimization method such as branch-and-bound or CP-SAT, allowing the model to handle larger groups (10+ members) without evaluating every assignment. Second, the Euclidean distance cost can be extended to better represent real movement by incorporating intermediate waypoints or direction-dependent penalties rather than assuming every dancer travels along a straight line (because they don't, obviously). Third, collision screening could include time: instead of flagging any two intersecting paths, dancers' positions could be interpolated throughout the transition and a collision would only be flagged when two dancers occupy nearby positions at approximately the same moment.

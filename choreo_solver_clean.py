import math
from itertools import permutations

import numpy as np
from scipy.optimize import linear_sum_assignment


# ============================================================
# DATA
# ============================================================

SEQUENCE_1_FORMATIONS = {
    11: {"B": (0, -5), "T": (0, -2), "A": (-4, -2), "W": (0, -1), "Y": (4, -2)},
    12: {"B": (-8, -5), "T": (-10, -4), "A": (-12, -2), "W": (-8, -1), "Y": (-4, -2)},
    13: {"B": (-11, -3), "T": (-2, -1), "A": (-12, 1), "W": (-12, 2), "Y": (-8, -4)},
    14: {"B": (-11, -3), "T": (7, -3), "A": (-12, 1), "W": (-12, 2), "Y": (-8, -4)},
    15: {"B": (-8, 0), "T": (0, -3), "A": (-2, 1), "W": (2, -2), "Y": (-4, -2)},
    16: {"B": (-4, 0), "T": (1, -3), "A": (4, 0), "W": (2, -2), "Y": (0, -1)},
}

SEQUENCE_1_FOCUS = {
    12: "T",
    13: "T",
    14: "T",
    15: "T",
    16: None,
}

SEQUENCE_2_FORMATIONS = {
    45: {"B": (-10, 2), "T": (-10, 0), "A": (0, 6), "W": (5, -2), "Y": (4, -1)},
    46: {"B": (-6, 4), "T": (3, 4), "A": (0, 4), "W": (2, -1), "Y": (4, -2)},
    47: {"B": (-6, 2), "T": (3, 2), "A": (0, 4), "W": (-3, 0), "Y": (6, 4)},
    48: {"B": (-6, 1), "T": (3, -1), "A": (0, 1), "W": (-3, -1), "Y": (6, 1)},
    49: {"B": (-6, -1), "T": (3, 2), "A": (0, -1), "W": (-3, 2), "Y": (6, -1)},
    50: {"B": (-6, -1), "T": (3, -1), "A": (0, -1), "W": (-3, -1), "Y": (6, -1)},
}

SEQUENCE_2_PAIR_CONSTRAINTS = {
    46: [("W", "Y", 3)],
}


# ============================================================
# GEOMETRY AND VALIDATION
# ============================================================

def distance(p1, p2):
    """Euclidean distance between two stage coordinates."""
    return math.dist(p1, p2)


def validate_formations(start_formation, target_formation):
    """Require the same dancers in both formations."""
    if set(start_formation) != set(target_formation):
        raise ValueError("Start and target formations must contain the same dancers.")


def original_choreography_distance(start_formation, target_formation):
    """Total movement when every dancer keeps their named target slot."""
    validate_formations(start_formation, target_formation)

    return sum(
        distance(start_formation[dancer], target_formation[dancer])
        for dancer in start_formation
    )


def paths_intersect(p1, p2, q1, q2):
    """
    Check whether two straight-line movement segments properly cross.

    This is only a geometric screening tool. It does not model timing,
    body size, curved paths, or collinear/touching cases.
    """

    def orientation(a, b, c):
        value = (
            (b[1] - a[1]) * (c[0] - b[0])
            - (b[0] - a[0]) * (c[1] - b[1])
        )

        if abs(value) < 1e-9:
            return 0

        return 1 if value > 0 else 2

    o1 = orientation(p1, p2, q1)
    o2 = orientation(p1, p2, q2)
    o3 = orientation(q1, q2, p1)
    o4 = orientation(q1, q2, p2)

    return o1 != o2 and o3 != o4


def find_path_crossings(assignments):
    """Return dancer pairs whose straight-line paths cross."""
    crossings = []

    for i in range(len(assignments)):
        for j in range(i + 1, len(assignments)):
            a = assignments[i]
            b = assignments[j]

            if paths_intersect(
                a["start_position"],
                a["target_position"],
                b["start_position"],
                b["target_position"],
            ):
                crossings.append((a["dancer"], b["dancer"]))

    return crossings


def satisfies_pair_constraints(assignments, pair_constraints=None):
    """
    Check maximum-distance constraints between dancer pairs.

    Example:
        [("W", "Y", 3)]
    means W and Y must finish no more than 3 units apart.
    """
    if not pair_constraints:
        return True

    positions = {
        item["dancer"]: item["target_position"]
        for item in assignments
    }

    for dancer_1, dancer_2, max_distance in pair_constraints:
        if distance(positions[dancer_1], positions[dancer_2]) > max_distance:
            return False

    return True


# ============================================================
# ASSIGNMENT HELPERS
# ============================================================

def build_assignments(start_formation, target_formation, dancers, target_names):
    """Convert a dancer-to-slot mapping into readable assignment records."""
    assignments = []
    total_distance = 0.0

    for dancer, target_name in zip(dancers, target_names):
        start = start_formation[dancer]
        target = target_formation[target_name]
        movement_distance = distance(start, target)

        assignments.append({
            "dancer": dancer,
            "start_position": start,
            "target_slot": target_name,
            "target_position": target,
            "distance": movement_distance,
        })

        total_distance += movement_distance

    return assignments, total_distance


def add_focus_penalty(cost_matrix, dancers, target_names, focus_dancer, penalty):
    """Softly penalize another dancer taking the focal dancer's slot."""
    weighted_matrix = cost_matrix.copy()

    for i, dancer in enumerate(dancers):
        for j, target_name in enumerate(target_names):
            if target_name == focus_dancer and dancer != focus_dancer:
                weighted_matrix[i, j] += penalty

    return weighted_matrix


# ============================================================
# HUNGARIAN BASELINE
# ============================================================

def solve_transition(
    start_formation,
    target_formation,
    focus_dancer=None,
    focus_penalty=0,
):
    """
    Find a minimum-distance dancer-to-slot assignment with Hungarian.

    focus_penalty is optional and acts as a soft constraint.
    """
    validate_formations(start_formation, target_formation)

    dancers = list(start_formation)
    target_names = list(target_formation)
    targets = [target_formation[name] for name in target_names]

    cost_matrix = np.array(
        [
            [
                distance(start_formation[dancer], target)
                for target in targets
            ]
            for dancer in dancers
        ],
        dtype=float,
    )

    weighted_matrix = cost_matrix.copy()

    if focus_dancer is not None and focus_penalty > 0:
        weighted_matrix = add_focus_penalty(
            cost_matrix,
            dancers,
            target_names,
            focus_dancer,
            focus_penalty,
        )

    rows, cols = linear_sum_assignment(weighted_matrix)

    assignments = []

    for row, col in zip(rows, cols):
        assignments.append({
            "dancer": dancers[row],
            "start_position": start_formation[dancers[row]],
            "target_slot": target_names[col],
            "target_position": targets[col],
            "distance": float(cost_matrix[row, col]),
        })

    total_distance = float(cost_matrix[rows, cols].sum())

    return assignments, total_distance


# ============================================================
# EXHAUSTIVE SEARCH FOR PAIRWISE CONSTRAINTS
# ============================================================

def generate_assignments(
    start_formation,
    target_formation,
    focus_dancer=None,
    require_focus=False,
    pair_constraints=None,
):
    """
    Generate every dancer-to-slot assignment that satisfies hard constraints.

    This is practical for small groups. For five dancers, only 5! = 120
    assignments are checked.
    """
    validate_formations(start_formation, target_formation)

    dancers = list(start_formation)
    target_names = list(target_formation)

    for target_permutation in permutations(target_names):
        assignment_map = dict(zip(dancers, target_permutation))

        if (
            require_focus
            and focus_dancer is not None
            and assignment_map[focus_dancer] != focus_dancer
        ):
            continue

        assignments, total_distance = build_assignments(
            start_formation,
            target_formation,
            dancers,
            target_permutation,
        )

        if not satisfies_pair_constraints(assignments, pair_constraints):
            continue

        yield assignments, total_distance, assignment_map


def solve_constrained(
    start_formation,
    target_formation,
    focus_dancer=None,
    require_focus=False,
    pair_constraints=None,
    focus_penalty=0,
    collision_penalty=0,
):
    """
    Minimize movement plus optional focus and crossing penalties.

    Exhaustive search is used because path crossings and pair-distance rules
    depend on complete assignments rather than independent dancer-slot costs.
    """
    best_result = None
    best_score = float("inf")

    for assignments, total_distance, assignment_map in generate_assignments(
        start_formation,
        target_formation,
        focus_dancer=focus_dancer,
        require_focus=require_focus,
        pair_constraints=pair_constraints,
    ):
        focus_cost = 0

        if (
            focus_dancer is not None
            and assignment_map[focus_dancer] != focus_dancer
        ):
            focus_cost = focus_penalty

        crossings = find_path_crossings(assignments)

        score = (
            total_distance
            + focus_cost
            + collision_penalty * len(crossings)
        )

        if score < best_score:
            best_score = score

            best_result = {
                "assignments": assignments,
                "distance": total_distance,
                "crossings": crossings,
                "score": score,
            }

    return best_result


def find_best_crossing_free(
    start_formation,
    target_formation,
    focus_dancer=None,
    pair_constraints=None,
):
    """
    Find the shortest crossing-free assignment under hard constraints.

    Returns (None, None) when no such assignment exists.
    """
    best_assignments = None
    best_distance = float("inf")

    for assignments, total_distance, _ in generate_assignments(
        start_formation,
        target_formation,
        focus_dancer=focus_dancer,
        require_focus=(focus_dancer is not None),
        pair_constraints=pair_constraints,
    ):
        if (
            not find_path_crossings(assignments)
            and total_distance < best_distance
        ):
            best_assignments = assignments
            best_distance = total_distance

    if best_assignments is None:
        return None, None

    return best_assignments, best_distance


# ============================================================
# ANALYSIS
# ============================================================

def analyze_transition(
    start_formation,
    target_formation,
    focus_dancer=None,
    pair_constraints=None,
):
    """
    Compare the original choreography, Hungarian baseline,
    constrained optimum, and crossing-free feasibility.
    """
    original_distance = original_choreography_distance(
        start_formation,
        target_formation,
    )

    hungarian_assignments, hungarian_distance = solve_transition(
        start_formation,
        target_formation,
    )

    hungarian_crossings = find_path_crossings(hungarian_assignments)

    constrained_result = solve_constrained(
        start_formation,
        target_formation,
        focus_dancer=focus_dancer,
        require_focus=(focus_dancer is not None),
        pair_constraints=pair_constraints,
    )

    crossing_free_assignments, crossing_free_distance = (
        find_best_crossing_free(
            start_formation,
            target_formation,
            focus_dancer=focus_dancer,
            pair_constraints=pair_constraints,
        )
    )

    return {
        "original_distance": original_distance,
        "hungarian_distance": hungarian_distance,
        "hungarian_crossings": hungarian_crossings,
        "constrained_distance": constrained_result["distance"],
        "constrained_crossings": constrained_result["crossings"],
        "crossing_free_exists": crossing_free_assignments is not None,
        "crossing_free_distance": crossing_free_distance,
    }


def analyze_sequence(
    formations,
    focus_by_formation=None,
    pair_constraints_by_formation=None,
):
    """Analyze every consecutive transition in a formation sequence."""
    focus_by_formation = focus_by_formation or {}
    pair_constraints_by_formation = pair_constraints_by_formation or {}

    formation_numbers = sorted(formations)
    results = []

    for start_id, target_id in zip(
        formation_numbers[:-1],
        formation_numbers[1:],
    ):
        result = analyze_transition(
            formations[start_id],
            formations[target_id],
            focus_dancer=focus_by_formation.get(target_id),
            pair_constraints=pair_constraints_by_formation.get(target_id),
        )

        result["start_id"] = start_id
        result["target_id"] = target_id

        results.append(result)

    return results


def print_sequence_summary(title, results):
    """Print a compact comparison table."""
    print(f"\n{title}")

    print(
        "Transition | Original | Hungarian | H-Cross | "
        "Constrained | C-Cross | Crossing-Free? | CF Distance"
    )

    for result in results:
        cf_distance = result["crossing_free_distance"]
        cf_text = "-" if cf_distance is None else f"{cf_distance:.2f}"

        print(
            f'{result["start_id"]} → {result["target_id"]} | '
            f'{result["original_distance"]:.2f} | '
            f'{result["hungarian_distance"]:.2f} | '
            f'{len(result["hungarian_crossings"])} | '
            f'{result["constrained_distance"]:.2f} | '
            f'{len(result["constrained_crossings"])} | '
            f'{"Yes" if result["crossing_free_exists"] else "No"} | '
            f'{cf_text}'
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    sequence_1_results = analyze_sequence(
        SEQUENCE_1_FORMATIONS,
        focus_by_formation=SEQUENCE_1_FOCUS,
    )

    print_sequence_summary(
        "SEQUENCE 1: FORMATIONS 11 → 16",
        sequence_1_results,
    )

    sequence_2_results = analyze_sequence(
        SEQUENCE_2_FORMATIONS,
        pair_constraints_by_formation=SEQUENCE_2_PAIR_CONSTRAINTS,
    )

    print_sequence_summary(
        "SEQUENCE 2: FORMATIONS 45 → 50",
        sequence_2_results,
    )

DP_COMPLEXITY_LIMIT = 20_000_000     # n * target_paise budget for DP
DFS_CANDIDATE_LIMIT = 40             # DFS branching stays manageable below this
CPSAT_TIME_LIMIT_SECONDS = 5         # hard wall-clock cap per group, keeps a batch run bounded
CPSAT_CANDIDATE_LIMIT = 500          # sane upper bound even for CP-SAT — beyond this, flag not solve


def _to_paise(amount) -> int:
    return round(amount * 100)


def subset_sum_dp(candidates, target_paise: int) -> dict:
    """0/1 subset-sum DP — unchanged, this is still the fastest path
    for small targets."""
    amounts_paise = [_to_paise(c["amount"]) for c in candidates]

    cnt = [0] * (target_paise + 1)
    parent = [(-1, -1)] * (target_paise + 1)
    cnt[0] = 1

    for i, amt in enumerate(amounts_paise):
        if amt <= 0 or amt > target_paise:
            continue
        for s in range(target_paise, amt - 1, -1):
            prev = cnt[s - amt]
            if prev == 0:
                continue
            if cnt[s] == 0:
                parent[s] = (s - amt, i)
            cnt[s] = min(2, cnt[s] + prev)

    if cnt[target_paise] == 0:
        return {"subset": None, "ambiguous": False, "method": "dp"}

    result_indices = []
    s = target_paise
    while s > 0:
        prev_sum, idx = parent[s]
        result_indices.append(idx)
        s = prev_sum

    return {
        "subset": [candidates[i] for i in result_indices],
        "ambiguous": cnt[target_paise] >= 2,
        "method": "dp",
    }


def subset_sum_dfs(candidates, target_paise: int, max_solutions: int = 2, max_nodes: int = 200_000) -> dict:
    """Branch-and-bound DFS — unchanged except a node budget so a bad
    case degrades to 'too_complex' instead of hanging."""
    items = sorted(enumerate(candidates), key=lambda pair: -_to_paise(pair[1]["amount"]))
    n = len(items)

    suffix_sum = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix_sum[i] = suffix_sum[i + 1] + _to_paise(items[i][1]["amount"])

    solutions: list[list[int]] = []
    path: list[int] = []
    nodes = {"count": 0}

    def backtrack(i: int, remaining: int):
        nodes["count"] += 1
        if nodes["count"] > max_nodes:
            raise RuntimeError("node_budget_exceeded")
        if len(solutions) >= max_solutions:
            return
        if remaining == 0:
            solutions.append(list(path))
            return
        if i >= n or remaining < 0:
            return
        if suffix_sum[i] < remaining:
            return

        orig_idx, item = items[i]
        amt = _to_paise(item["amount"])

        path.append(orig_idx)
        backtrack(i + 1, remaining - amt)
        path.pop()
        if len(solutions) >= max_solutions:
            return
        backtrack(i + 1, remaining)

    try:
        backtrack(0, target_paise)
    except RuntimeError:
        return {"subset": None, "ambiguous": False, "method": "too_complex"}

    if not solutions:
        return {"subset": None, "ambiguous": False, "method": "dfs"}

    return {
        "subset": [candidates[i] for i in solutions[0]],
        "ambiguous": len(solutions) > 1,
        "method": "dfs",
    }


def subset_sum_cpsat(candidates, target_paise: int, tolerance_paise: int = 0) -> dict:
    """CP-SAT fallback for the genuinely hard territory: large n AND
    large target, where DP's O(n*target) blows the memory/time budget
    and DFS's branching factor is too wide to prune effectively.

    This is where OR-Tools earns its keep — its learned-clause pruning
    and LP-relaxation bounds beat hand-rolled backtracking by a wide
    margin at this scale. We ask two questions, not one, to get the
    same ambiguity signal the DP/DFS paths give:
      1. Is there ANY subset hitting the target (within tolerance)?
      2. Is there a SECOND, different subset also hitting it?
    """
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return {"subset": None, "ambiguous": False, "method": "too_complex",
                "detail": "ortools_not_installed"}

    n = len(candidates)
    if n > CPSAT_CANDIDATE_LIMIT:
        return {"subset": None, "ambiguous": False, "method": "too_complex",
                "detail": "candidate_count_exceeds_cpsat_limit"}

    amounts_paise = [_to_paise(c["amount"]) for c in candidates]

    def _solve(forbid_solution=None):
        model = cp_model.CpModel()
        x = [model.NewBoolVar(f"x{i}") for i in range(n)]
        total = sum(x[i] * amounts_paise[i] for i in range(n))
        model.Add(total >= target_paise - tolerance_paise)
        model.Add(total <= target_paise + tolerance_paise)

        # At least one item selected — an empty subset trivially satisfies
        # target=0 but that's never a meaningful reconciliation result.
        model.Add(sum(x) >= 1)

        if forbid_solution is not None:
            # Exclude the exact same 0/1 assignment so re-solving finds a
            # genuinely different subset, not the same one again.
            same_as_prev = []
            for i, was_selected in enumerate(forbid_solution):
                same_as_prev.append(x[i] if was_selected else x[i].Not())
            model.Add(sum(same_as_prev) <= n - 1)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = CPSAT_TIME_LIMIT_SECONDS
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            selected = [solver.Value(x[i]) == 1 for i in range(n)]
            return selected
        return None

    first = _solve()
    if first is None:
        return {"subset": None, "ambiguous": False, "method": "cpsat"}

    second = _solve(forbid_solution=first)

    subset = [candidates[i] for i in range(n) if first[i]]

    return {
        "subset": subset,
        "ambiguous": second is not None,
        "method": "cpsat",
    }


def subset_sum_search(candidates, target, tolerance_paise: int = 0) -> dict:
    """Dispatcher — routes to whichever algorithm's weak dimension
    isn't the problem for this particular group.

      DP    : fast when target is small, regardless of n
      DFS   : fast when n is small, regardless of target (good pruning)
      CPSAT : the genuinely hard case — large n AND large target —
              where DP's array blows memory and DFS's branching factor
              is too wide. This used to be an automatic 'too_complex',
              now it's an automatic solver call instead.
    """
    target_paise = _to_paise(target)
    n = len(candidates)

    if target_paise <= 0:
        return {"subset": None, "ambiguous": False, "method": "none"}

    total_available = sum(_to_paise(c["amount"]) for c in candidates)
    if target_paise > total_available + tolerance_paise:
        return {"subset": None, "ambiguous": False, "method": "none"}

    if n * target_paise <= DP_COMPLEXITY_LIMIT and tolerance_paise == 0:
        return subset_sum_dp(candidates, target_paise)

    if n <= DFS_CANDIDATE_LIMIT and tolerance_paise == 0:
        return subset_sum_dfs(candidates, target_paise)

    # Large n and/or large target and/or fee-tolerance search space —
    # this is exactly where hand-rolled search stops scaling. Try the
    # real solver before giving up.
    return subset_sum_cpsat(candidates, target_paise, tolerance_paise)
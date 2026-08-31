DP_TARGET_PAISE_LIMIT = 2_000_000   # ₹20,000 — DP array stays small below this
DFS_CANDIDATE_LIMIT = 40             # DFS branching stays manageable below this
 
 
def _to_paise(amount) -> int:
    return round(amount * 100)
 
 
def subset_sum_dp(candidates, target_paise: int) -> dict:
    """0/1 subset-sum DP that also counts (capped at 2) how many
    distinct subsets reach the target — this is what turns a silent
    arbitrary pick into an honest ambiguity flag."""
    amounts_paise = [_to_paise(c["amount"]) for c in candidates]
 
    cnt = [0] * (target_paise + 1)      # capped subset-count per sum, 0/1/2("2+")
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
                parent[s] = (s - amt, i)   # first path found — used for reconstruction
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
 
 
def subset_sum_dfs(candidates, target_paise: int, max_solutions: int = 2) -> dict:
    """Branch-and-bound DFS, sorted descending for better pruning, with
    a suffix-sum feasibility check and an early stop once 2 distinct
    solutions are found (we only need to know IF it's ambiguous, not
    enumerate every possibility)."""
    items = sorted(enumerate(candidates), key=lambda pair: -_to_paise(pair[1]["amount"]))
    n = len(items)
 
    suffix_sum = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix_sum[i] = suffix_sum[i + 1] + _to_paise(items[i][1]["amount"])
 
    solutions: list[list[int]] = []
    path: list[int] = []
 
    def backtrack(i: int, remaining: int):
        if len(solutions) >= max_solutions:
            return
        if remaining == 0:
            solutions.append(list(path))
            return
        if i >= n or remaining < 0:
            return
        if suffix_sum[i] < remaining:   # can't reach target even taking everything left
            return
 
        orig_idx, item = items[i]
        amt = _to_paise(item["amount"])
 
        path.append(orig_idx)
        backtrack(i + 1, remaining - amt)
        path.pop()
        if len(solutions) >= max_solutions:
            return
        backtrack(i + 1, remaining)
 
    backtrack(0, target_paise)
 
    if not solutions:
        return {"subset": None, "ambiguous": False, "method": "dfs"}
 
    return {
        "subset": [candidates[i] for i in solutions[0]],
        "ambiguous": len(solutions) > 1,
        "method": "dfs",
    }
 
 
def subset_sum_search(candidates, target) -> dict:
    """Dispatcher — routes to whichever algorithm's weak dimension
    isn't the problem for this particular group."""
    target_paise = _to_paise(target)
    n = len(candidates)
 
    if target_paise <= 0:
        return {"subset": None, "ambiguous": False, "method": "none"}
 
    total_available = sum(_to_paise(c["amount"]) for c in candidates)
    if target_paise > total_available:
        return {"subset": None, "ambiguous": False, "method": "none"}
 
    if target_paise <= DP_TARGET_PAISE_LIMIT:
        return subset_sum_dp(candidates, target_paise)
 
    if n <= DFS_CANDIDATE_LIMIT:
        return subset_sum_dfs(candidates, target_paise)
 
    # Large target AND large N — genuinely hard territory. Don't force
    # a computation that could hang; report it honestly instead.
    return {"subset": None, "ambiguous": False, "method": "too_complex"}
 
def subset_sum_search(candidiates, target):
    amounts_paise = [round(c["amount"] * 100) for c in candidiates]
    target_paise = round(target * 100)
    
    if target_paise <= 0 or target_paise > sum(amounts_paise):
        return None
    
    dp = [False] * (target_paise + 1)
    parent = [(-1, -1)] * (target_paise + 1)
    dp[0] = True
    
    for i, amt in enumerate(amounts_paise):
        for s in range(target_paise, amt - 1, -1):
            if not dp[s] and dp[s - amt]:
                dp[s] = True
                parent[s] = (s - amt, i)
                
    if not dp[target_paise]:
        return None
    
    result_indices = []
    s = target_paise
    while s > 0:
        prev_sum, idx = parent[s]
        result_indices.append(idx)
        s = prev_sum
    
    return [candidiates[i] for i in result_indices]
    
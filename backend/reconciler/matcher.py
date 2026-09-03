from .algorithm import subset_sum_search
from .constants import CRITICAL_AMOUNT_THRESHOLD,FEE_EPSILON,FEE_PCT,GST_PCT,AMOUNT_TOLERANCE, DATE_TOLERANCE_DAYS
from datetime import timedelta

#======= Expected value after fee =========#

def expected_net_after_fee(amount):
    fee = round(amount * FEE_PCT, 2)
    gst = round(fee * GST_PCT, 2) 
    return round(amount - fee - gst, 2), fee, gst

def within_date_tolerance(g_date, b_date, days=DATE_TOLERANCE_DAYS):
    return abs((b_date - g_date)) <= timedelta(days=days)

#============== Helper functions ==========#

def _risk_for_amount(base_risk: str, amount: float) -> str:

    if base_risk in ("medium", "high") and amount is not None and amount >= CRITICAL_AMOUNT_THRESHOLD:
        return "critical"
    return base_risk


def step_exact_match(gateway_rows, bank_by_utr, matched_payment_ids, matches):
    """Step 2: same UTR, same amount — resolves the easy majority for free."""
    for g in gateway_rows:
        if g["payment_id"] in matched_payment_ids:
            continue
        for b in bank_by_utr.get(g["utr_norm"], []):
            if b["amount"] == g["amount"]:
                matches.append({
                    "payment_id": g["payment_id"], "match_type": "exact",
                    "matched_amount": g["amount"], "bank_amount": b["amount"],
                    "risk": "low",
                    "explanation": "Exact UTR and amount match.",
                })
                matched_payment_ids.add(g["payment_id"])
                break


def step_lump_sum_unbundling(gateway_by_utr, bank_by_utr, matched_payment_ids, matches, exceptions):
    """Step 3: a UTR shared by >1 unmatched gateway row is a lump-sum
    candidate group — subset-sum search decomposes one bank credit
    into the individual payments it represents; leftovers become a
    distinct, explained exception type rather than a mystery."""
    for utr, group in gateway_by_utr.items():
        if utr is None:
            continue
        unmatched_group = [g for g in group if g["payment_id"] not in matched_payment_ids]
        if len(unmatched_group) < 2:
            continue
 
        for b in bank_by_utr.get(utr, []):
            result = subset_sum_search(unmatched_group, b["amount"])
 
            if result["method"] == "too_complex":
                for g in unmatched_group:
                    exceptions.append({
                        "payment_id": g["payment_id"],
                        "reason_code": "lump_sum_too_complex",
                        "reason_detail": None,
                        "recommended_action": (
                            "This lump-sum group is too large to safely auto-resolve — "
                            "reconcile manually against the payout schedule."
                        ),
                        "risk": "high",
                        "amount": g["amount"],
                    })
                    matched_payment_ids.add(g["payment_id"])
                break
 
            subset = result["subset"]
            if not subset:
                continue
 
            if result["ambiguous"]:
                for g in unmatched_group:
                    exceptions.append({
                        "payment_id": g["payment_id"],
                        "reason_code": "ambiguous_lump_sum_match",
                        "reason_detail": None,
                        "recommended_action": (
                            f"More than one combination of payments sums to this bank "
                            f"credit of {b['amount']} under UTR {utr} — cannot auto-resolve "
                            f"with confidence, needs manual review."
                        ),
                        "risk": "critical",
                        "amount": g["amount"],
                    })
                    matched_payment_ids.add(g["payment_id"])
                break
 
            for g in subset:
                matches.append({
                    "payment_id": g["payment_id"], "match_type": "lump_sum",
                    "matched_amount": g["amount"], "bank_amount": b["amount"],
                    "risk": "medium",
                    "explanation": (
    f"Part of a bulk settlement of {b['amount']} "
    f"covering {len(subset)} payments under UTR {utr}."
),
                })
                matched_payment_ids.add(g["payment_id"])
 
            held_back = [g for g in unmatched_group if g not in subset]
            for g in held_back:
                exceptions.append({
                    "payment_id": g["payment_id"],
                    "reason_code": "held_back_from_lump_sum",
                    "reason_detail": None,
                    "recommended_action": (
                        "Likely a rolling reserve or pending refund — "
                        "verify against gateway payout schedule."
                    ),
                    "risk": _risk_for_amount("medium", g["amount"]),
                    "amount": g["amount"],
                })
                matched_payment_ids.add(g["payment_id"])  # resolved as an exception
            break

def step_fuzzy_match(gateway_rows, bank_by_utr, matched_payment_ids, matches):
    for g in gateway_rows:
        if g["payment_id"] in matched_payment_ids:
            continue    
        
        for b in bank_by_utr.get(g["utr_norm"], []):
            if (abs(b["amount"] - g["amount"]) <= AMOUNT_TOLERANCE
                and within_date_tolerance(g["created_at"], b["credited_at"])):
                matches.append({
                    "payment_id": g["payment_id"], "match_type": "fuzzy",
                    "matched_amount": g["amount"], "bank_amount": b["amount"],
                    "risk": "low",
                    "explanation": (
                        f"Amount within tolerance (delta {round(abs(b['amount'] - g['amount']),2)}) "
                        f"and settlement date within {DATE_TOLERANCE_DAYS} days."
                    ),
                })
                matched_payment_ids.add(g["payment_id"])
                break
            
def step_fee_aware_check(gateway_rows, bank_by_utr, matched_payment_ids, matches):
    for g in gateway_rows:
        if g["payment_id"] in matched_payment_ids:
            continue
        expected_net, fee, gst = expected_net_after_fee(g["amount"])
        for b in bank_by_utr.get(g["utr_norm"], []):
            if abs(b["amount"] - expected_net) <= FEE_EPSILON:
                matches.append({
                    "payment_id": g["payment_id"], "match_type": "fee_aware",
                    "matched_amount": g["amount"], "bank_amount": b["amount"],
                    "risk": "low",
                    "explanation": (
                        f"Gap of {round(g['amount']-b['amount'],2)} fully explained by "
                        f"{FEE_PCT*100:.0f}% gateway fee ({fee}) + {GST_PCT*100:.0f}% GST on fee ({gst})."
                    ),
                })
                matched_payment_ids.add(g["payment_id"])
                break
    
def step_near_miss_utr(gateway_rows, bank_rows, matched_payment_ids, matches):
        for g in gateway_rows:
            if g["payment_id"] in matched_payment_ids or not g["utr_norm"]:
                continue
            for b in bank_rows:
                if not b["utr_norm"]:
                    continue
                close_utr = (b["utr_norm"].startswith(g["utr_norm"][:6])
                         or g["utr_norm"].startswith(b["utr_norm"][:6]))
                if close_utr and abs(b["amount"] - g["amount"]) <= AMOUNT_TOLERANCE:
                    matches.append({
                        "payment_id": g["payment_id"], "match_type": "fuzzy",
                        "matched_amount": g["amount"], "bank_amount": b["amount"],
                        "risk": "medium",
                        "explanation": (
                            f"UTR reference partially matches ({g['utr']} vs {b['utr']}); "
                            f"amount matches within tolerance."
                        ),
                    })
                    matched_payment_ids.add(g["payment_id"])
                    break
            
def step_log_remaining_as_exceptions(gateway_rows, bank_by_utr, matched_payment_ids, exceptions):
    for g in gateway_rows:
        if g["payment_id"] in matched_payment_ids:
            continue
        if not g["utr_norm"] or g["utr_norm"] not in bank_by_utr:
            reason_code = "no_corresponding_bank_record"
            action = "Check whether the payment ever reached the bank; verify webhook/settlement logs."
            
        else:
            reason_code = "amount_or_date_mismatch_unresolved"
            
            action = "Manually compare gateway and bank records for this UTR."
        exceptions.append({
            "payment_id": g["payment_id"],
            "reason_code": reason_code,
            "reason_detail": None,   
            "recommended_action": action,
            "risk": "high",
            "amount": g["amount"],
        })

#============= Main function =========#
        
def run_matching(gateway_rows, bank_rows):
    """It returns matches and exception lists"""
    matches = []
    exceptions = []
    
    matched_payment_ids = set()
    
    bank_by_utr = {}
    for b in bank_rows:
        bank_by_utr.setdefault(b["utr_norm"], []).append(b)
        
    gateway_by_utr = {}
    for g in gateway_rows:
        gateway_by_utr.setdefault(g["utr_norm"], []).append(g)
        
    #======= Extracting exact matches ======#    
    
    step_exact_match(gateway_rows, bank_by_utr, matched_payment_ids, matches)

    #============ Lump-sum unbundling =======#
    
    step_lump_sum_unbundling(gateway_by_utr, bank_by_utr, matched_payment_ids, matches, exceptions)

    #============ Fuzzy Match ===========#
    
    step_fuzzy_match(gateway_rows, bank_by_utr, matched_payment_ids, matches)
    
    #============ Deterministic Formula check (2% fee + 18% GST) =======#
    
    step_fee_aware_check(gateway_rows, bank_by_utr, matched_payment_ids, matches)
    
    #============= Garbled / Trucated UTR ============#
    step_near_miss_utr(gateway_rows, bank_rows, matched_payment_ids, matches)
    
    #=============== Exception Tagging ==============#
    
    step_log_remaining_as_exceptions(gateway_rows, bank_by_utr, matched_payment_ids, exceptions)
            
    return matches, exceptions
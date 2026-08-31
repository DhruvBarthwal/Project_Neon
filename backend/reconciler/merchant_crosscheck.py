from .matcher import _risk_for_amount  # reuse the same critical-tier escalation logic


def cross_check_merchant(gateway_rows, merchant_rows, matched_payment_ids, exceptions):
    gateway_by_order = {g["order_id"]: g for g in gateway_rows if g.get("order_id")}
    merchant_by_order = {m["order_id"]: m for m in merchant_rows}

    for g in gateway_rows:
        if g["payment_id"] not in matched_payment_ids:
            continue  # only checking payments that DID settle on the gateway+bank side
        order_id = g.get("order_id")
        if not order_id:
            continue

        merchant_row = merchant_by_order.get(order_id)
        if merchant_row is None or merchant_row["status"] != "paid":
            exceptions.append({
                "payment_id": g["payment_id"],
                "reason_code": "merchant_status_lag",
                "reason_detail": None,
                "recommended_action": (
                    "Payment settled on gateway and bank, but the merchant's own "
                    "system hasn't reflected it — check webhook delivery for this order."
                ),
                "risk": _risk_for_amount("medium", g["amount"]),
                "amount": g["amount"],
            })


    for order_id, m in merchant_by_order.items():
        if m["status"] != "paid":
            continue
        gateway_row = gateway_by_order.get(order_id)
        gateway_confirms = gateway_row is not None and gateway_row["payment_id"] in matched_payment_ids

        if not gateway_confirms:
            exceptions.append({
                "payment_id": m.get("payment_id") or f"merchant_claim_{order_id}",
                "reason_code": "unverified_merchant_claim",
                "reason_detail": None,
                "recommended_action": (
                    "Merchant system marked this order paid, but no successfully "
                    "reconciled gateway payment backs the claim — verify before trusting it."
                ),
                "risk": "critical",   # always critical — an unverified paid claim is a real integrity risk
                "amount": m["amount"],
            })

    return exceptions
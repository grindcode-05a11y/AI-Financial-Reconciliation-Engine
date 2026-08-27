import pandas as pd
import json
import numpy as np
import os
import streamlit as st
from test import normalize_and_validate_datasets, categorize_exception

def analyze_financial_exceptions_with_fin_ai(summary_metrics, exception_list):
    """
    Generates pure Executive Risk & Financial Loss Exposure analysis without generic mitigation advice.
    """
    if not exception_list:
        return {
            "executive_summary": "* **System Status:** Optimal. Zero operational risks or settlement mismatches detected.",
            "loss_analysis": "* **Direct Capital Exposure:** ₹0.00\n* **Regulatory & Operational Liability:** Minimal liability across processed volume."
        }
    
    df_exc = pd.DataFrame(exception_list)
    top_issue = df_exc['issue_category'].mode()[0] if ('issue_category' in df_exc.columns and not df_exc.empty) else "N/A"
    high_sev_count = len(df_exc[df_exc['severity'] == 'High']) if 'severity' in df_exc.columns else 0
    total_stuck = df_exc['paid_amount'].sum() if 'paid_amount' in df_exc.columns else 0.0

    high_risk_vol = df_exc[df_exc['severity'] == 'High']['paid_amount'].sum() if 'severity' in df_exc.columns else 0.0
    med_risk_vol = df_exc[df_exc['severity'] == 'Medium']['paid_amount'].sum() if 'severity' in df_exc.columns else 0.0
    est_leakage = (high_risk_vol * 0.15) + (med_risk_vol * 0.05)

    exec_summary = (
        f"* **Primary Bottleneck Identified:** `{top_issue}` accounts for the primary share of settlement failures.\n"
        f"* **Financial Risk Exposure:** **₹{total_stuck:,.2f}** total transaction volume currently flagged in unresolved/review states.\n"
        f"* **Critical Vulnerabilities:** **{high_sev_count} high-severity exceptions** require immediate treasury intervention."
    )

    loss_analysis = (
        f"* **Direct Capital Exposure:** **₹{high_risk_vol:,.2f}** locked in high-severity un-reconciled states with active settlement blockage.\n"
        f"* **Estimated Annual Revenue Leakage:** **₹{est_leakage:,.2f}** projected loss from payment processor discrepancies, chargeback penalties, and manual operational overhead.\n"
        f"* **Operational Risk Index:** High. Unlinked ledger references introduce compliance audit risks under standard merchant settlement timelines."
    )

    return {
        "executive_summary": exec_summary,
        "loss_analysis": loss_analysis
    }

def run_ai_reconciliation(sample_size=None, orders_path='orders.csv', payments_path='payments.csv', custom_dfs=None):
    if custom_dfs:
        raw_orders, raw_payments = custom_dfs
    else:
        raw_orders = pd.read_csv(orders_path)
        raw_payments = pd.read_csv(payments_path)

    orders_df, payments_df = normalize_and_validate_datasets(raw_orders, raw_payments)

    if sample_size and sample_size < len(payments_df):
        payments_batch = payments_df.head(sample_size).copy()
    else:
        payments_batch = payments_df.copy()

    reconciled_list = []
    exception_list = []

    orders_deduped = orders_df.drop_duplicates(subset=['norm_order_id'], keep='first')
    orders_indexed = orders_deduped.set_index('norm_order_id').to_dict('index')

    for idx, pay_row in payments_batch.iterrows():
        p_id = str(pay_row.get('std_pay_id', f"PAY_{idx}")).strip()
        o_id_raw = str(pay_row.get('std_order_id', 'MISSING_ID')).strip()
        norm_o_id = str(pay_row.get('norm_order_id', '')).strip()

        pay_amount = float(pay_row.get('std_amount', 0.0))
        fee = float(pay_row.get('std_fee', 0.0))
        raw_status = str(pay_row.get('std_status', 'Success')).strip()

        if norm_o_id not in orders_indexed:
            meta = categorize_exception("MISSING_ORDER")
            exception_list.append({
                "record_id": p_id,
                "order_id": o_id_raw,
                "paid_amount": pay_amount,
                "fee": fee,
                "issue_category": meta["category"],
                "issue": meta["detail"],
                "severity": meta["severity"],
                "action": meta["action"]
            })
            continue

        order_record = orders_indexed[norm_o_id]
        order_amount = float(order_record.get('std_amount', pay_amount))

        if raw_status not in ['Success', 'Captured', 'Completed', 'Settled', 'Delivered']:
            meta = categorize_exception("STATUS_MISMATCH", raw_status=raw_status)
            exception_list.append({
                "record_id": p_id,
                "order_id": o_id_raw,
                "paid_amount": pay_amount,
                "fee": fee,
                "issue_category": meta["category"],
                "issue": meta["detail"],
                "severity": meta["severity"],
                "action": meta["action"]
            })
            continue

        diff_direct = abs(pay_amount - order_amount)
        diff_net = abs((pay_amount + fee) - order_amount)

        if diff_direct <= 0.01 or diff_net <= 0.01:
            reconciled_list.append({
                "record_id": p_id,
                "order_id": o_id_raw,
                "amount": pay_amount,
                "fee": fee,
                "status": "RECONCILED",
                "confidence_score": 0.99
            })
        else:
            meta = categorize_exception("AMOUNT_DISCREPANCY", paid=pay_amount, expected=order_amount)
            exception_list.append({
                "record_id": p_id,
                "order_id": o_id_raw,
                "paid_amount": pay_amount,
                "fee": fee,
                "issue_category": meta["category"],
                "issue": meta["detail"],
                "severity": meta["severity"],
                "action": meta["action"]
            })

    total_records = len(payments_batch)
    matched_count = len(reconciled_list)
    match_rate = (matched_count / total_records * 100) if total_records > 0 else 0.0

    summary_metrics = {
        "total_records": total_records,
        "match_rate_pct": round(match_rate, 2),
        "reconciled_count": matched_count,
        "exception_count": len(exception_list)
    }

    ai_analysis_report = analyze_financial_exceptions_with_fin_ai(summary_metrics, exception_list)

    report_data = {
        "summary": summary_metrics,
        "reconciled": reconciled_list,
        "exceptions": exception_list,
        "ai_analysis": ai_analysis_report
    }

    with open('reconciliation_report.json', 'w') as f:
        json.dump(report_data, f, indent=4)

    return report_data

if __name__ == '__main__':
    run_ai_reconciliation()
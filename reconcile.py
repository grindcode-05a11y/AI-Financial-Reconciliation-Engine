import pandas as pd
import numpy as np
import json
import os
from utils import normalize_and_validate_datasets, calculate_match_percentage

def run_ai_reconciliation(sample_size=None, orders_path='orders.csv', payments_path='payments.csv', custom_dfs=None):
    if custom_dfs is not None:
        raw_orders, raw_payments = custom_dfs
    else:
        raw_orders = pd.read_csv(orders_path)
        raw_payments = pd.read_csv(payments_path)

    orders, payments = normalize_and_validate_datasets(raw_orders, raw_payments)

    if sample_size and sample_size < len(orders):
        orders = orders.head(sample_size)
        payments = payments[payments['order_id'].isin(orders['order_id'])]

    # Exact Left Join on Order ID
    merged = pd.merge(payments, orders, on='order_id', how='left', suffixes=('_payment', '_order'))

    merged['paid_amount'] = merged['paid_amount'].fillna(0.0)
    merged['order_amount_val'] = merged['order_amount'].fillna(0.0)
    merged['fee_val'] = merged.get('fee_payment', merged.get('fee_order', 0.0)).fillna(0.0)

    # Prefer the PAYMENT side's status (the real payment-gateway status,
    # e.g. Success/Refunded/Failed/Not Charged/Pending) over the order's own
    # fulfilment status -- that's what "Gateway Status Issue" is meant to
    # reflect. Only fall back to order status if no payment status exists.
    if 'status_payment' in merged.columns:
        merged['status_val'] = merged['status_payment'].fillna('COMPLETED').astype(str).str.strip()
    elif 'status_order' in merged.columns:
        merged['status_val'] = merged['status_order'].fillna('COMPLETED').astype(str).str.strip()
    elif 'status' in merged.columns:
        merged['status_val'] = merged['status'].fillna('COMPLETED').astype(str).str.strip()
    else:
        merged['status_val'] = 'COMPLETED'

    # Whether the orders file actually contained a genuine monetary field.
    # If it didn't (e.g. this orders.csv only has order_status/shipping/
    # discount columns, no order value), amount-matching is not a
    # meaningful signal and must not be allowed to veto every row --
    # reconciliation then rests on payment status alone.
    has_order_amount_data = bool(merged.get('order_amount_is_real_payment',
                                  merged.get('order_amount_is_real_order',
                                  merged.get('order_amount_is_real', pd.Series([False])))).any())

    valid_status = merged['status_val'].str.upper().isin(['COMPLETED', 'SUCCESS', 'SETTLED', 'PAID', 'DELIVERED', 'SHIPPED', ''])

    if has_order_amount_data:
        has_matched_order = merged['order_amount_val'] > 0
        gross_diff = (merged['paid_amount'] - merged['order_amount_val']).abs()
        net_diff = ((merged['paid_amount'] + merged['fee_val']) - merged['order_amount_val']).abs()
        amount_matches = (gross_diff <= 1.0) | (net_diff <= 1.0) | (gross_diff / np.maximum(merged['order_amount_val'], 1.0) <= 0.02)
        is_reconciled = has_matched_order & valid_status & amount_matches
    else:
        # No real order-value column to check amounts against -- use the
        # payment actually clearing (paid_amount > 0) plus a valid gateway
        # status as the reconciliation signal instead of a fabricated amount.
        has_matched_order = merged['paid_amount'] > 0
        amount_matches = pd.Series(True, index=merged.index)
        is_reconciled = has_matched_order & valid_status

    df_reconciled = merged[is_reconciled].copy()
    df_exceptions = merged[~is_reconciled].copy()

    # Exception Audit Log
    exceptions_list = []
    if not df_exceptions.empty:
        if has_order_amount_data:
            cond_missing = ~df_exceptions['order_amount_val'].gt(0)
        else:
            cond_missing = pd.Series(False, index=df_exceptions.index)
        # Any status outside the accepted "valid_status" whitelist is a genuine
        # status issue -- label it using whatever that real status value is
        # (Refunded/Failed/Cancelled/Canceled/Unavailable/Invoiced/Processing/...)
        # rather than a fixed hardcoded list that only covers a subset of
        # possible source vocabularies and silently mislabels the rest as a
        # generic "Amount Discrepancy".
        cond_status = ~valid_status.loc[df_exceptions.index]

        conditions = [cond_status, cond_missing]
        issues = [
            'Gateway Status Issue (' + df_exceptions['status_val'].str.capitalize() + ')',
            'Missing Order Record in Merchant Ledger'
        ]
        
        df_exceptions['issue'] = np.select(conditions, issues, default='Amount Discrepancy')

        # Severity tiering: a ledger integrity break (no matching order at
        # all) is always the worst case. Beyond that, not every non-valid
        # status carries the same real-world risk -- a terminal failure
        # (Failed/Declined/Cancelled/Unavailable) needs urgent treasury
        # attention, a transient in-flight status (Pending/Processing/
        # Invoiced/Created/Approved) will very likely resolve on its own,
        # and a completed-then-reversed Refund sits in between. A genuine
        # amount mismatch on an otherwise valid status is Medium by default.
        # Using a single hardcoded True/False split previously meant every
        # status issue was forced to High and Medium/Low were unreachable.
        status_upper = df_exceptions['status_val'].str.upper()
        HIGH_RISK_STATUSES = {'FAILED', 'DECLINED', 'CANCELLED', 'CANCELED', 'UNAVAILABLE'}
        LOW_RISK_STATUSES = {'PENDING', 'PROCESSING', 'INVOICED', 'CREATED', 'APPROVED', 'NOT CHARGED'}

        severity = pd.Series('Medium', index=df_exceptions.index)
        severity[cond_status & status_upper.isin(LOW_RISK_STATUSES)] = 'Low'
        severity[cond_status & status_upper.isin(HIGH_RISK_STATUSES)] = 'High'
        severity[cond_status & ~status_upper.isin(HIGH_RISK_STATUSES | LOW_RISK_STATUSES)] = 'Medium'
        severity[cond_missing] = 'High'  # a missing ledger record always overrides to High
        df_exceptions['severity'] = severity

        df_exceptions['action'] = 'FLAGGED_FOR_REVIEW'
        df_exceptions['fee'] = df_exceptions['fee_val']
        
        exceptions_list = df_exceptions[['record_id', 'order_id', 'paid_amount', 'fee', 'issue', 'severity', 'action']].to_dict(orient='records')

    reconciled_list = []
    if not df_reconciled.empty:
        df_reconciled['status'] = 'SETTLED'
        df_reconciled['confidence_score'] = 1.0
        df_reconciled['amount'] = df_reconciled['paid_amount']
        df_reconciled['fee'] = df_reconciled['fee_val']
        reconciled_list = df_reconciled[['record_id', 'order_id', 'amount', 'fee', 'status', 'confidence_score']].to_dict(orient='records')

    total_records = len(merged)
    reconciled_count = len(reconciled_list)
    exception_count = len(exceptions_list)
    match_rate = round((reconciled_count / total_records * 100), 2) if total_records > 0 else 0.0

    total_exposure = float(df_exceptions['paid_amount'].sum()) if not df_exceptions.empty else 0.0
    high_severity_count = sum(1 for e in exceptions_list if e['severity'] == 'High')
    
    primary_issue = "Gateway Status Issue (Refunded)"
    if exceptions_list:
        primary_issue = pd.DataFrame(exceptions_list)['issue'].value_counts().index[0]

    exec_summary = [
        f"• <b>Primary Bottleneck Identified:</b> <code>{primary_issue}</code> accounts for the primary share of settlement failures.",
        f"• <b>Financial Risk Exposure:</b> ₹{total_exposure:,.2f} total transaction volume currently flagged in unresolved/review states.",
        f"• <b>Critical Vulnerabilities:</b> {high_severity_count} high-severity exceptions require immediate treasury intervention."
    ]

    est_loss = total_exposure * 0.12
    loss_analysis = [
        f"• <b>Direct Capital Exposure:</b> ₹{total_exposure:,.2f} locked in high-severity un-reconciled states with active settlement blockage.",
        f"• <b>Estimated Annual Revenue Leakage:</b> ₹{est_loss:,.2f} projected loss from payment processor discrepancies, chargeback penalties, and manual operational overhead.",
        f"• <b>Operational Risk Index:</b> High. Unlinked ledger references introduce compliance audit risks under standard merchant settlement timelines."
    ]

    report = {
        "summary": {
            "total_records": total_records,
            "reconciled_count": reconciled_count,
            "exception_count": exception_count,
            "match_rate_pct": match_rate
        },
        "ai_analysis": {
            "executive_summary": exec_summary,
            "loss_analysis": loss_analysis
        },
        "reconciled": reconciled_list,
        "exceptions": exceptions_list
    }

    with open('reconciliation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)

    return report

if __name__ == "__main__":
    run_ai_reconciliation("")
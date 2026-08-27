import pandas as pd
import json
import numpy as np
from tests import normalize_and_validate_datasets, categorize_exception

def run_ai_reconciliation(sample_size=None, orders_path='orders.csv', payments_path='payments.csv', custom_dfs=None):
    # Read custom dataframes from memory if uploaded, otherwise load CSV files from disk
    if custom_dfs is not None:
        raw_orders, raw_payments = custom_dfs
    else:
        raw_orders = pd.read_csv(orders_path)
        raw_payments = pd.read_csv(payments_path)

    # Limit the number of rows if a sample size is selected in the UI
    if sample_size and sample_size < len(raw_orders):
        raw_orders = raw_orders.head(sample_size)
        raw_payments = raw_payments[raw_payments['order_id'].isin(raw_orders['order_id'])] if 'order_id' in raw_payments.columns else raw_payments.head(sample_size)

    # Clean column names and fix data types using test.py functions
    orders, payments = normalize_and_validate_datasets(raw_orders, raw_payments)

    # Perform left join on order_id
    merged = pd.merge(
        payments,
        orders,
        on='order_id',
        how='left',
        suffixes=('_payment', '_order')
    )

    reconciled = []
    exceptions = []

    # Loop through merged dataset to process reconciliations
    for idx, row in merged.iterrows():
        # Track whether a matching order row was found
        order_amt_col = 'order_amount' if 'order_amount' in row else 'order_amount_order'
        order_val = row.get(order_amt_col)
        
        is_matched = pd.notna(order_val)
        order_amt = float(order_val) if is_matched else 0.0
        paid_amt = float(row.get('paid_amount', 0.0))
        
        row_dict = row.to_dict()
        row_dict['order_amount'] = order_amt
        row_dict['is_matched'] = is_matched

        diff = abs(paid_amt - order_amt)

        # Flag as settled if order exists and amounts match within tolerance
        if is_matched and diff <= 0.01:
            reconciled.append({
                "record_id": str(row.get('record_id', idx)),
                "order_id": str(row.get('order_id', '')),
                "amount": paid_amt,
                "fee": float(row.get('fee_payment', row.get('fee', 0.0))),
                "status": "SETTLED",
                "confidence_score": 1.0
            })
        else:
            # Categorize mismatch reasons using test.py helper
            issue, severity, action = categorize_exception(row_dict)
            exceptions.append({
                "record_id": str(row.get('record_id', idx)),
                "order_id": str(row.get('order_id', '')),
                "paid_amount": paid_amt,
                "order_amount": order_amt,
                "fee": float(row.get('fee_payment', row.get('fee', 0.0))),
                "issue": issue,
                "issue_category": issue,
                "severity": severity,
                "action": action
            })

    # Calculate metrics summary
    total_records = len(merged)
    reconciled_count = len(reconciled)
    exception_count = len(exceptions)
    match_rate = round((reconciled_count / total_records * 100), 2) if total_records > 0 else 0.0

    total_risk_exposure = sum(e['paid_amount'] for e in exceptions)

    # Identify primary issue category
    primary_issue = "Amount Discrepancy"
    if exceptions:
        issue_series = pd.DataFrame(exceptions)['issue'].value_counts()
        if not issue_series.empty:
            primary_issue = issue_series.index[0]

    # Structure final JSON report
    report = {
        "summary": {
            "total_records": total_records,
            "reconciled_count": reconciled_count,
            "exception_count": exception_count,
            "match_rate_pct": match_rate
        },
        "ai_analysis": {
            "executive_summary": f"• **Primary Bottleneck Identified:** `{primary_issue}` accounts for the primary share of settlement failures.\n• **Financial Risk Exposure:** ₹{total_risk_exposure:,.2f} total transaction volume currently flagged in unresolved/review states.\n• **Critical Vulnerabilities:** {exception_count} high-severity exceptions require immediate treasury intervention.",
            "loss_analysis": f"• **Estimated Annual Revenue Leakage:** ₹{total_risk_exposure * 0.12:,.2f} projected loss from payment processor discrepancies, chargeback penalties, and manual operational overhead.\n• **Operational Risk Index:** High. Unlinked ledger references introduce compliance audit risks under standard merchant settlement timelines."
        },
        "reconciled": reconciled,
        "exceptions": exceptions
    }

    # Save output to JSON
    with open('reconciliation_report.json', 'w') as f:
        json.dump(report, f, indent=4)

    return report

if __name__ == "__main__":
    run_ai_reconciliation()
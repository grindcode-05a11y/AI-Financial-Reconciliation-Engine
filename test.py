import pandas as pd
import numpy as np

def normalize_and_validate_datasets(orders_df, payments_df):
    """
    Normalizes arbitrary external datasets (e.g., Brazilian Olist, Amazon, Kaggle)
    into a unified internal schema for downstream reconciliation.
    """
    orders_df = orders_df.copy()
    payments_df = payments_df.copy()

    orders_df.columns = orders_df.columns.str.strip().str.lower()
    payments_df.columns = payments_df.columns.str.strip().str.lower()

    # Dynamic column resolution across varied schemas
    order_id_orders = next((c for c in orders_df.columns if 'order_id' in c or 'order' in c), orders_df.columns[0])
    order_id_pay = next((c for c in payments_df.columns if 'order_id' in c or 'order' in c), payments_df.columns[0])

    pay_id_col = next((c for c in payments_df.columns if 'payment' in c or 'txn' in c or 'pay_id' in c), payments_df.columns[0])
    amount_pay_col = next((c for c in payments_df.columns if 'payment_value' in c or 'amount' in c or 'paid' in c or 'price' in c), payments_df.columns[1])
    amount_order_col = next((c for c in orders_df.columns if 'total' in c or 'amount' in c or 'price' in c or 'value' in c), orders_df.columns[1])

    # Clean IDs for precise lookup matching
    orders_df['norm_order_id'] = orders_df[order_id_orders].astype(str).str.strip().str.lower().str.replace(r'\.0$', '', regex=True)
    payments_df['norm_order_id'] = payments_df[order_id_pay].astype(str).str.strip().str.lower().str.replace(r'\.0$', '', regex=True)

    # Re-map standard column references for downstream consumption
    orders_df['std_order_id'] = orders_df[order_id_orders]
    orders_df['std_amount'] = pd.to_numeric(orders_df[amount_order_col], errors='coerce').fillna(0.0)

    payments_df['std_pay_id'] = payments_df[pay_id_col]
    payments_df['std_order_id'] = payments_df[order_id_pay]
    payments_df['std_amount'] = pd.to_numeric(payments_df[amount_pay_col], errors='coerce').fillna(0.0)

    fee_col = next((c for c in payments_df.columns if 'fee' in c), None)
    payments_df['std_fee'] = pd.to_numeric(payments_df[fee_col], errors='coerce').fillna(0.0) if fee_col else 0.0

    status_col = next((c for c in payments_df.columns if 'status' in c or 'state' in c), None)
    payments_df['std_status'] = payments_df[status_col].astype(str).str.strip().str.capitalize() if status_col else 'Success'

    return orders_df, payments_df

def categorize_exception(issue_type, raw_status=None, paid=0.0, expected=0.0):
    """
    Categorizes exception details into clean, fixed taxonomy strings.
    """
    if issue_type == "MISSING_ORDER":
        return {
            "category": "Missing Order Record",
            "detail": "Missing Order Record in Merchant Ledger",
            "severity": "High",
            "action": "FLAGGED_UNRESOLVED"
        }
    elif issue_type == "STATUS_MISMATCH":
        sev = "High" if raw_status in ['Failed', 'User_dropped', 'Cancelled', 'Canceled'] else "Medium"
        return {
            "category": "Gateway Status Issue",
            "detail": f"Gateway Status Issue ({raw_status})",
            "severity": sev,
            "action": "FLAGGED_FOR_REVIEW"
        }
    elif issue_type == "AMOUNT_DISCREPANCY":
        return {
            "category": "Amount Discrepancy",
            "detail": f"Amount Discrepancy (Paid: {paid:.2f}, Expected: {expected:.2f})",
            "severity": "High",
            "action": "ROUTED_TO_EXCEPTION"
        }
    return {
        "category": "Unclassified Exception",
        "detail": "General System Mismatch",
        "severity": "Medium",
        "action": "FLAGGED_FOR_REVIEW"
    }
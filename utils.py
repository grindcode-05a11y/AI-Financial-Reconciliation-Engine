import pandas as pd
import numpy as np

COLUMN_MAPPINGS = {
    'orders': {
        'order_id': ['order_id', 'id', 'transaction_id', 'order_number', 'order_ref', 'oid'],
        'order_amount': ['order_amount', 'amount', 'total_amount', 'price', 'payment_value', 'value', 'order_value'],
        'fee': ['fee', 'service_fee', 'commission', 'platform_fee', 'gateway_fee'],
        'status': ['status', 'order_status', 'state', 'payment_status']
    },
    'payments': {
        'record_id': ['record_id', 'payment_id', 'id', 'trans_id', 'txn_id', 'pay_id'],
        'order_id': ['order_id', 'order_ref', 'transaction_id', 'oid'],
        'paid_amount': ['paid_amount', 'amount', 'amount_paid', 'payment_value', 'price', 'settled_amount', 'value'],
        'fee': ['fee', 'service_fee', 'commission', 'platform_fee', 'gateway_fee', 'transaction_fee'],
        'status': ['status', 'payment_status', 'gateway_status', 'state']
    }
}

def clean_currency_series(series):
    if series is None:
        return pd.Series(0.0)
    return (
        series.astype(str)
        .str.replace(r'[₹$,\s]', '', regex=True)
        .pipe(pd.to_numeric, errors='coerce')
        .fillna(0.0)
    )

def normalize_columns(df, dataset_type):
    mapping = COLUMN_MAPPINGS.get(dataset_type, {})
    df_clean = df.copy()
    df_clean.columns = [str(c).strip().lower() for c in df_clean.columns]
    
    renames = {}
    for target_col, synonyms in mapping.items():
        for syn in synonyms:
            if syn.lower() in df_clean.columns:
                renames[syn.lower()] = target_col
                break
                
    return df_clean.rename(columns=renames)

def normalize_and_validate_datasets(orders_df, payments_df):
    orders = normalize_columns(orders_df, 'orders')
    payments = normalize_columns(payments_df, 'payments')

    # If the orders file has no genuine monetary field (e.g. it only has
    # order_status/shipping/discount_percentage-style columns), do NOT
    # silently grab the first numeric column (like discount_percentage) and
    # pretend it's the order value -- comparing a %-discount against a real
    # paid_amount will make every single row fail the amount check.
    # Leave it as NaN so downstream logic knows there's no real order value
    # to reconcile against, and status becomes the reconciliation signal.
    if 'order_amount' not in orders.columns:
        orders['order_amount'] = np.nan
        orders['order_amount_is_real'] = False
    else:
        orders['order_amount_is_real'] = True

    if 'paid_amount' not in payments.columns:
        num_cols = payments.select_dtypes(include=[np.number]).columns
        payments['paid_amount'] = payments[num_cols[0]] if len(num_cols) > 0 else 0.0

    if 'status' not in orders.columns: orders['status'] = 'COMPLETED'
    if 'fee' not in orders.columns: orders['fee'] = 0.0
    if 'fee' not in payments.columns: payments['fee'] = 0.0

    if 'order_id' not in orders.columns: orders['order_id'] = orders.index.astype(str)
    if 'record_id' not in payments.columns: payments['record_id'] = payments.index.astype(str)
    if 'order_id' not in payments.columns: payments['order_id'] = payments.index.astype(str)

    orders['order_id'] = orders['order_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
    payments['order_id'] = payments['order_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()
    payments['record_id'] = payments['record_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()

    orders['order_amount'] = clean_currency_series(orders['order_amount'])
    payments['paid_amount'] = clean_currency_series(payments['paid_amount'])
    orders['fee'] = clean_currency_series(orders['fee'])
    payments['fee'] = clean_currency_series(payments['fee'])

    return orders, payments

def calculate_match_percentage(reference_path_or_df, custom_path_or_df):
    """Loads or accepts a reference dataset and a custom dataset, aligns them,
    and calculates the exact mathematical matching percentage.
    """
    ref_df = pd.read_csv(reference_path_or_df) if isinstance(reference_path_or_df, str) else reference_path_or_df
    custom_df = pd.read_csv(custom_path_or_df) if isinstance(custom_path_or_df, str) else custom_path_or_df

    common_cols = list(set(ref_df.columns).intersection(set(custom_df.columns)))
    if not common_cols:
        return 0.0

    ref_subset = ref_df[common_cols].sort_index()
    custom_subset = custom_df[common_cols].sort_index()

    min_rows = min(len(ref_subset), len(custom_subset))
    ref_subset = ref_subset.iloc[:min_rows]
    custom_subset = custom_subset.iloc[:min_rows]

    match_matrix = ref_subset.eq(custom_subset)
    total_cells = match_matrix.size
    matched_cells = match_matrix.sum().sum()

    match_percentage = (matched_cells / total_cells) * 100 if total_cells > 0 else 0.0
    return round(match_percentage, 2)
import pandas as pd
import json
import numpy as np
import requests
import os
import streamlit as st

# Hugging Face Inference API configuration for specialized financial LLM
HF_API_URL = "https://api-inference.huggingface.co/models/FinGPT/fingpt-forecaster_dow30_llama2-7b_lora"


def analyze_financial_exceptions_with_fin_ai(summary_metrics, exception_list):
    """
    Sends aggregated metrics and sample exception logs to a specialized financial AI.
    Falls back to a local structured audit report if the API is offline or returns an error.
    """
    # Safely retrieve from Streamlit secrets, environment variables, or empty string CLI fallback
    HF_API_KEY = ""
    try:
        HF_API_KEY = st.secrets.get("HF_API_KEY", "")
    except Exception:
        HF_API_KEY = os.getenv("HF_API_KEY", "")

    # Fallback generator for offline/unreachable API states or local runs
    def build_local_fallback():
        if not exception_list:
            return "#### Executive AI Audit Briefing & Risk Assessment\n\n* **System Status:** Optimal. Zero operational risks or settlement mismatches detected in this ledger batch."
        
        df_exc = pd.DataFrame(exception_list)
        top_issue = df_exc['issue'].mode()[0] if not df_exc.empty else "N/A"
        high_sev_count = len(df_exc[df_exc['severity'] == 'High']) if 'severity' in df_exc.columns else 0
        total_stuck = df_exc['paid_amount'].sum() if 'paid_amount' in df_exc.columns else 0.0

        return f"""#### Executive AI Audit Briefing & Risk Assessment

* **Primary Bottleneck Identified:** `{top_issue}` accounts for the primary share of settlement failures.
* **Financial Risk Exposure:** **₹{total_stuck:,.2f}** total transaction volume currently flagged in unresolved/review states.
* **Critical Vulnerabilities:** **{high_sev_count} high-severity exceptions** require immediate treasury intervention.

---

**Strategic Mitigation Recommendations:**
1. **Gateway API Retry Protocol:** Implement 3-way asynchronous polling for gateway timeouts (`Gateway Status Issue`).
2. **Fee Variance Thresholds:** Audit payment processor settlement fee structures against internal merchant ledger settings.
3. **Escalation Path:** Trigger automated webhooks to the Risk Operations team for high-value transactions exceeding ₹10,000 stuck in review."""

    if not HF_API_KEY or HF_API_KEY == "hf_your_actual_api_key_here":
        return build_local_fallback()

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    prompt = f"""[TASK: FINANCIAL AUDIT & RISK ANALYSIS]
Analyze the following settlement engine execution logs:
- Total Processed Ledger: {summary_metrics.get('total_records')}
- Match Rate: {summary_metrics.get('match_rate_pct')}%
- Exception Count: {summary_metrics.get('exception_count')}

Sample Flagged Exception Records:
{json.dumps(exception_list[:5], indent=2)}

Provide an executive mitigation strategy focusing on:
1. Operational Gateway Risk
2. Estimated Revenue at Risk
3. Actionable Mitigation Steps for Treasury & Accounting"""

    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 400, "temperature": 0.2}
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=10)
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            return result[0].get('generated_text', build_local_fallback())
        elif isinstance(result, dict) and 'generated_text' in result:
            return result.get('generated_text')
        else:
            return build_local_fallback()
            
    except Exception:
        return build_local_fallback()


def run_ai_reconciliation(sample_size=None):
    payments_df = pd.read_csv('payments.csv')
    orders_df = pd.read_csv('orders.csv')

    if sample_size and sample_size < len(payments_df):
        payments_batch = payments_df.head(sample_size).copy()
    else:
        payments_batch = payments_df.copy()

    reconciled_list = []
    exception_list = []

    orders_indexed = orders_df.set_index('order_id').to_dict('index')

    for idx, pay_row in payments_batch.iterrows():
        p_id = str(pay_row.get('payment_id', f"PAY_{idx}"))
        o_id = str(pay_row.get('order_id', 'MISSING_ID'))
        
        try:
            pay_amount = float(pay_row.get('amount_paid', 0.0))
            if np.isnan(pay_amount): pay_amount = 0.0
        except (ValueError, TypeError):
            pay_amount = 0.0

        try:
            fee = float(pay_row.get('transaction_fee', 0.0))
            if np.isnan(fee): fee = 0.0
        except (ValueError, TypeError):
            fee = 0.0

        raw_status = str(pay_row.get('payment_status', 'Unknown')).strip().capitalize()
        
        # Missing Order Record -> High Severity
        if o_id not in orders_indexed:
            exception_list.append({
                "record_id": p_id,
                "order_id": o_id,
                "paid_amount": pay_amount,
                "fee": fee,
                "issue": "Missing Order Record in Merchant Ledger",
                "severity": "High",
                "action": "FLAGGED_UNRESOLVED"
            })
            continue

        order_record = orders_indexed[o_id]
        
        try:
            order_amount = float(order_record.get('total_amount', pay_amount))
            if np.isnan(order_amount): order_amount = pay_amount
        except (ValueError, TypeError):
            order_amount = pay_amount

        # Gateway Status Issues with Dynamic Severity Scoring
        if raw_status not in ['Success', 'Captured', 'Completed']:
            severity_level = "High" if raw_status in ['Failed', 'User_dropped'] else "Medium"
            exception_list.append({
                "record_id": p_id,
                "order_id": o_id,
                "paid_amount": pay_amount,
                "fee": fee,
                "issue": f"Gateway Status Issue ({raw_status})",
                "severity": severity_level,
                "action": "FLAGGED_FOR_REVIEW"
            })
            continue

        # Amount Reconciliation Logic
        diff_direct = abs(pay_amount - order_amount)
        diff_net = abs((pay_amount + fee) - order_amount)

        if diff_direct <= 0.01 or diff_net <= 0.01:
            reconciled_list.append({
                "record_id": p_id,
                "order_id": o_id,
                "amount": pay_amount,
                "fee": fee,
                "status": "RECONCILED",
                "confidence_score": 0.99
            })
        else:
            exception_list.append({
                "record_id": p_id,
                "order_id": o_id,
                "paid_amount": pay_amount,
                "fee": fee,
                "issue": f"Amount Discrepancy (Paid: {pay_amount}, Expected: {order_amount})",
                "severity": "High",
                "action": "ROUTED_TO_EXCEPTION"
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
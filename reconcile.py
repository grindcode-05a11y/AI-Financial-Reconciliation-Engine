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
    Sends aggregated metrics and exception logs to FinGPT to dynamically generate 
    both the audit briefing and targeted strategic mitigations.
    """
    HF_API_KEY = ""
    try:
        HF_API_KEY = st.secrets.get("HF_API_KEY", "")
    except Exception:
        HF_API_KEY = os.getenv("HF_API_KEY", "")

    # Dynamic fallback: Aggregates real data metrics instead of hardcoded strings
    def build_local_fallback():
        if not exception_list:
            return "#### Executive AI Audit Briefing & Risk Assessment\n\n* **System Status:** Optimal. Zero operational risks or settlement mismatches detected in this ledger batch."
        
        df_exc = pd.DataFrame(exception_list)
        top_issue = df_exc['issue'].mode()[0] if not df_exc.empty else "N/A"
        high_sev_count = len(df_exc[df_exc['severity'] == 'High']) if 'severity' in df_exc.columns else 0
        total_stuck = df_exc['paid_amount'].sum() if 'paid_amount' in df_exc.columns else 0.0

        # Build dynamic recommendations based on detected exception categories
        dynamic_recommendations = []
        issues_text = " ".join(df_exc['issue'].tolist())

        if "Missing Order" in issues_text:
            dynamic_recommendations.append("1. **Order Sync Pipeline Audit:** Re-index asynchronous webhooks between merchant database and checkout gateway to resolve missing ledger references.")
        if "Gateway Status" in issues_text:
            dynamic_recommendations.append(f"{len(dynamic_recommendations) + 1}. **Automated Polling Protocol:** Implement a 3-way retry mechanism for payment statuses flagged under `{top_issue}`.")
        if "Amount Discrepancy" in issues_text:
            dynamic_recommendations.append(f"{len(dynamic_recommendations) + 1}. **Fee Structure Reconciliation:** Recalibrate dynamic gateway processing fees against raw transaction amounts to eliminate minor rounding variances.")

        if not dynamic_recommendations:
            dynamic_recommendations.append("1. **Treasury Escalation:** Initiate manual review for high-value unclassified ledger mismatches.")

        rec_str = "\n".join(dynamic_recommendations)

        return f"""#### Executive AI Audit Briefing & Risk Assessment

* **Primary Bottleneck Identified:** `{top_issue}` accounts for the primary share of settlement failures.
* **Financial Risk Exposure:** **₹{total_stuck:,.2f}** total transaction volume currently flagged in unresolved/review states.
* **Critical Vulnerabilities:** **{high_sev_count} high-severity exceptions** require immediate treasury intervention.

---

**Strategic Mitigation Recommendations (Generated from Data):**
{rec_str}"""

    if not HF_API_KEY or HF_API_KEY == "hf_your_actual_api_key_here":
        return build_local_fallback()

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # Explicit prompt instructing FinGPT to generate dynamic strategic mitigations
    prompt = f"""[TASK: FINANCIAL AUDIT & DYNAMIC STRATEGIC MITIGATION]
You are an expert AI Financial Controller. Analyze these settlement logs:
- Total Ledger Records: {summary_metrics.get('total_records')}
- Verified Match Rate: {summary_metrics.get('match_rate_pct')}%
- Total Exceptions: {summary_metrics.get('exception_count')}

Sample Exception Log:
{json.dumps(exception_list[:5], indent=2)}

Generate a response with two distinct sections:
1. Executive AI Audit Briefing & Risk Assessment (summarizing top issue, revenue at risk, and critical vulnerabilities).
2. Strategic Mitigation Recommendations (provide 3 customized, dynamic action steps specifically tailored to solve the exact exceptions listed above for Treasury and Engineering)."""

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.3,
            "return_full_text": False
        }
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=12)
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            generated_text = result[0].get('generated_text', '')
            return generated_text.strip() if generated_text.strip() else build_local_fallback()
        elif isinstance(result, dict) and 'generated_text' in result:
            generated_text = result.get('generated_text', '')
            return generated_text.strip() if generated_text.strip() else build_local_fallback()
        else:
            return build_local_fallback()
            
    except Exception:
        return build_local_fallback()


def run_ai_reconciliation(sample_size=None):
    payments_df = pd.read_csv('payments.csv')
    orders_df = pd.read_csv('orders.csv')

    # Clean header whitespace
    payments_df.columns = payments_df.columns.str.strip()
    orders_df.columns = orders_df.columns.str.strip()

    if sample_size and sample_size < len(payments_df):
        payments_batch = payments_df.head(sample_size).copy()
    else:
        payments_batch = payments_df.copy()

    reconciled_list = []
    exception_list = []

    # Safe deduplication of orders to prevent Pandas to_dict('index') ValueError
    orders_deduped = orders_df.drop_duplicates(subset=['order_id'], keep='first')
    orders_indexed = orders_deduped.set_index('order_id').to_dict('index')

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
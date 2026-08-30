import streamlit as st
import json
import pandas as pd
import plotly.express as px
from reconcile import run_ai_reconciliation

st.set_page_config(page_title="Enterprise AI Finance Controller", layout="wide")

st.markdown("""
<style>
    .stApp { 
        background: linear-gradient(135deg, #E0F2FE 0%, #F1F5F9 50%, #FCE7F3 100%) !important; 
        color: #0F172A !important; 
    }
    [data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 1.5rem !important; }
    [data-testid="stSidebar"] { background: rgba(255, 255, 255, 0.75) !important; backdrop-filter: blur(10px); }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, div[role="radiogroup"] label, label, .stMarkdown p, h1, h2, h3, h4, span { 
        color: #0F172A !important; 
        font-weight: 600 !important; 
    }
    
    .metric-card { 
        background: rgba(255, 255, 255, 0.85); 
        border: 1px solid rgba(203, 213, 225, 0.8); 
        border-radius: 12px; 
        padding: 16px; 
        text-align: center; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .metric-value { font-size: 2.1rem; font-weight: 700; margin-top: 4px; }
    .metric-label { font-size: 0.8rem; color: #475569 !important; text-transform: uppercase; font-weight: 700; }
    
    .briefing-card {
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(203, 213, 225, 0.8);
        border-left: 5px solid #0284C7;
        border-radius: 12px;
        padding: 24px;
        margin-top: 15px;
        margin-bottom: 25px;
    }
    .briefing-card p {
        line-height: 1.8;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

if 'dataset_mode' not in st.session_state:
    st.session_state['dataset_mode'] = 'primary'

st.sidebar.title("Control Panel")
st.sidebar.caption("Deterministic Engine Batch Controls")
st.sidebar.markdown("---")

if st.sidebar.button("Reset to Primary Dataset (CSV)", key="btn_reset_dataset", type="secondary", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state['dataset_mode'] = 'primary'
    
    with st.spinner("Restoring primary dataset..."):
        run_ai_reconciliation(sample_size=None, orders_path='orders.csv', payments_path='payments.csv')
    st.sidebar.success("Reset successful!")
    st.rerun()

st.sidebar.markdown("<br>", unsafe_allow_html=True)

data_scale = st.sidebar.radio(
    "Select Batch Sample Size:",
    ["100 Records", "1,000 Records", "10,000 Records", "Full Dataset"]
)
size_mapping = {"100 Records": 100, "1,000 Records": 1000, "10,000 Records": 10000, "Full Dataset": None}

if st.sidebar.button("Execute Settlement Engine", type="primary", use_container_width=True):
    with st.spinner("Processing transaction ledgers..."):
        if st.session_state.get('dataset_mode') == 'custom' and 'df_custom_orders' in st.session_state:
            run_ai_reconciliation(sample_size=size_mapping[data_scale], custom_dfs=(st.session_state['df_custom_orders'], st.session_state['df_custom_payments']))
        else:
            run_ai_reconciliation(sample_size=size_mapping[data_scale], orders_path='orders.csv', payments_path='payments.csv')
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Custom Dataset Upload (Optional)")

uploaded_orders = st.sidebar.file_uploader("Upload Orders CSV", type=["csv"], key="uploader_orders")
uploaded_payments = st.sidebar.file_uploader("Upload Payments CSV", type=["csv"], key="uploader_payments")

if uploaded_orders and uploaded_payments:
    if st.sidebar.button("Process Uploaded CSVs", type="secondary", use_container_width=True):
        df_orders_upload = pd.read_csv(uploaded_orders)
        df_payments_upload = pd.read_csv(uploaded_payments)
        
        st.session_state['df_custom_orders'] = df_orders_upload
        st.session_state['df_custom_payments'] = df_payments_upload
        st.session_state['dataset_mode'] = 'custom'
        
        with st.spinner("Normalizing schema and processing custom upload..."):
            run_ai_reconciliation(sample_size=None, custom_dfs=(df_orders_upload, df_payments_upload))
        st.sidebar.success("Custom dataset analyzed!")
        st.rerun()

st.title("Enterprise AI Finance Controller")
st.caption("Automated Settlement Platform & Autonomous Exception Advisor")

try:
    with open('reconciliation_report.json', encoding='utf-8') as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    reconciled = data.get('reconciled', [])
    exceptions = data.get('exceptions', [])
    ai_analysis = data.get('ai_analysis', {})

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Processed Ledger</div><div class='metric-value'>{summary.get('total_records', 0):,}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>Verified Match Rate</div><div class='metric-value' style='color:#15803D;'>{summary.get('match_rate_pct', 0.0)}%</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>Auto-Settled Records</div><div class='metric-value' style='color:#0284C7;'>{summary.get('reconciled_count', 0):,}</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-label'>Exceptions Flagged</div><div class='metric-value' style='color:#BE123C;'>{summary.get('exception_count', 0):,}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Domain-Specific Financial AI Briefing")
    
    exec_bullets = "<br>".join(ai_analysis.get('executive_summary', []))
    loss_bullets = "<br>".join(ai_analysis.get('loss_analysis', []))
    
    briefing_html = f"""
    <div class='briefing-card'>
        <h4 style='margin-top:0;'>Executive AI Audit Briefing & Risk Assessment</h4>
        <p>{exec_bullets}</p>
        <br>
        <h4>Financial Loss Risk & Exposure Analysis</h4>
        <p>{loss_bullets}</p>
    </div>
    """
    st.markdown(briefing_html, unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Resolution Breakdown")
        status_df = pd.DataFrame({
            'Status': ['Reconciled', 'Exceptions'],
            'Count': [summary.get('reconciled_count', 0), summary.get('exception_count', 0)]
        })
        fig_pie = px.pie(
            status_df, 
            values='Count', 
            names='Status', 
            color='Status',
            color_discrete_map={'Reconciled': '#0284C7', 'Exceptions': '#BE123C'},
            hole=0.45
        )
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        st.subheader("Exception Categories")
        if exceptions:
            df_exc = pd.DataFrame(exceptions)
            issue_counts = df_exc['issue'].value_counts().reset_index()
            issue_counts.columns = ['Category', 'Count']
            issue_counts = issue_counts.sort_values(by='Count', ascending=True)

            fig_bar = px.bar(
                issue_counts, 
                y='Category', 
                x='Count', 
                orientation='h',
                color_discrete_sequence=['#BE123C']
            )
            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                xaxis_title="Count", 
                yaxis_title=""
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No exceptions present to display category chart.")

    st.markdown("---")
    
    st.subheader("Transaction History & Exception Audit Log")
    
    view_mode = st.radio(
        "Select View Mode:",
        ["Flagged Exceptions Audit", "Auto-Settled Records"],
        horizontal=True
    )

    filter_col1, filter_col2 = st.columns([3, 1])
    with filter_col1:
        search_query = st.text_input("Quick Search (Order ID / Record ID):", "").strip().upper()
    with filter_col2:
        severity_filter = st.selectbox("Severity Level:", ["All", "High", "Medium", "Low"])

    target_data = exceptions if view_mode == "Flagged Exceptions Audit" else reconciled
    
    if target_data:
        df_table = pd.DataFrame(target_data)
        
        if 'severity' in df_table.columns and severity_filter != "All":
            df_table = df_table[df_table['severity'] == severity_filter]

        if search_query:
            id_cols = [c for c in ['order_id', 'record_id'] if c in df_table.columns]
            if id_cols:
                mask = df_table[id_cols].apply(lambda r: r.astype(str).str.contains(search_query).any(), axis=1)
                df_table = df_table[mask]

        if view_mode == "Flagged Exceptions Audit":
            col_rename = {
                'record_id': 'Payment ID',
                'order_id': 'Order ID',
                'paid_amount': 'Amount Paid',
                'fee': 'Fee',
                'issue': 'Audit Exception Reason',
                'severity': 'Severity',
                'action': 'Resolution Status',
                'ai_risk_score': 'AI Risk Score',
                'agent_reasoning': 'AI Agent Reasoning'
            }
            df_display = df_table.rename(columns=col_rename)
            if 'Amount Paid' in df_display.columns:
                df_display['Amount Paid'] = df_display['Amount Paid'].apply(lambda x: f"₹{x:,.2f}")
            if 'Fee' in df_display.columns:
                df_display['Fee'] = df_display['Fee'].apply(lambda x: f"₹{x:,.2f}")
        else:
            col_rename = {
                'record_id': 'Payment ID',
                'order_id': 'Order ID',
                'amount': 'Amount Paid',
                'fee': 'Fee',
                'status': 'Resolution Status',
                'confidence_score': 'Confidence Score',
                'ai_risk_score': 'AI Risk Score'
            }
            df_display = df_table.rename(columns=col_rename)
            if 'Amount Paid' in df_display.columns:
                df_display['Amount Paid'] = df_display['Amount Paid'].apply(lambda x: f"₹{x:,.2f}")

        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info(f"No records found for {view_mode}.")

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
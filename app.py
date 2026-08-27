import streamlit as st
import json
import pandas as pd
import plotly.express as px
from reconcile import run_ai_reconciliation

st.set_page_config(
    page_title="Enterprise AI Finance Controller",
    layout="wide"
)

# Modern Soft Gradient Theme (Light Blue -> Soft Pink) + Styling
st.markdown("""
<style>
    /* Main Canvas Background */
    .stApp {
        background: linear-gradient(135deg, #E0F2FE 0%, #F1F5F9 50%, #FCE7F3 100%) !important;
        color: #0F172A !important;
    }

    /* Top Header Bar */
    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Container Top Padding */
    .block-container {
        padding-top: 2rem !important;
    }

    /* Translucent Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.65) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(203, 213, 225, 0.8) !important;
    }

    /* Typography & Contrast Adjustments */
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p,
    div[role="radiogroup"] label, 
    div[role="radiogroup"] label p, 
    div[role="radiogroup"] p,
    label, 
    .stMarkdown p,
    h1, h2, h3, h4, span {
        color: #0F172A !important;
        font-weight: 600 !important;
    }

    /* Metric Display Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(203, 213, 225, 0.8);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin-top: 4px;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #475569 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* AI Executive Strategic Insights Card */
    .ai-card {
        background: rgba(255, 255, 255, 0.95);
        border-left: 5px solid #0284C7;
        border-radius: 10px;
        padding: 20px;
        margin-top: 15px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }

    /* High-contrast Input Fields & Select Boxes */
    div[data-baseweb="input"],
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1.5px solid #64748B !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    }

    /* Focus State Accent */
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"]:focus-within > div {
        border-color: #0284C7 !important;
        box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.2) !important;
    }

    /* Input Text Options */
    input {
        color: #0F172A !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Control Panel
st.sidebar.title("Control Panel")
st.sidebar.caption("Deterministic Engine Batch Controls")
st.sidebar.markdown("---")

data_scale = st.sidebar.radio(
    "Select Batch Sample Size:",
    ["100 Records (Evaluation)", "1,000 Records", "10,000 Records", "Full Dataset (100k+)"]
)

size_mapping = {
    "100 Records (Evaluation)": 100,
    "1,000 Records": 1000,
    "10,000 Records": 10000,
    "Full Dataset (100k+)": None
}

st.sidebar.markdown("<br>", unsafe_allow_html=True)

if st.sidebar.button("Execute Settlement Engine", type="primary", use_container_width=True):
    with st.spinner("Processing transaction ledgers & invoking Financial AI analysis..."):
        run_ai_reconciliation(sample_size=size_mapping[data_scale])
    st.sidebar.success("Engine Execution Complete")
    st.rerun()

# Custom File Upload Section Below Existing Controls
st.sidebar.markdown("---")
st.sidebar.subheader("Custom Dataset Upload (Optional)")
uploaded_orders = st.sidebar.file_uploader("Upload Orders CSV", type=["csv"], key="custom_orders")
uploaded_payments = st.sidebar.file_uploader("Upload Payments CSV", type=["csv"], key="custom_payments")

if uploaded_orders and uploaded_payments:
    if st.sidebar.button("Process Uploaded CSVs", use_container_width=True):
        df_orders_upload = pd.read_csv(uploaded_orders)
        df_payments_upload = pd.read_csv(uploaded_payments)
        
        # Clean header spaces and deduplicate order_id column
        df_orders_upload.columns = df_orders_upload.columns.str.strip()
        df_payments_upload.columns = df_payments_upload.columns.str.strip()

        if 'order_id' in df_orders_upload.columns:
            df_orders_upload = df_orders_upload.drop_duplicates(subset=['order_id'], keep='first')

        # Persist target files locally for pipeline consumption
        df_orders_upload.to_csv("orders.csv", index=False)
        df_payments_upload.to_csv("payments.csv", index=False)
        
        with st.spinner("Running engine on uploaded custom datasets..."):
            run_ai_reconciliation(sample_size=None)
        st.sidebar.success("Custom Dataset Execution Complete")
        st.rerun()

# Title Header
st.title("Enterprise AI Finance Controller")
st.caption("Automated Settlement Platform & Autonomous Exception Advisor")
st.markdown("---")

# Main Pipeline Render
try:
    with open('reconciliation_report.json') as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    reconciled = data.get('reconciled', [])
    exceptions = data.get('exceptions', [])
    ai_analysis = data.get('ai_analysis', 'No AI analysis report available.')

    # Key Metric Indicator Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Processed Ledger</div><div class='metric-value' style='color:#0F172A;'>{summary.get('total_records', 0):,}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Verified Match Rate</div><div class='metric-value' style='color:#15803D;'>{summary.get('match_rate_pct', 0.0)}%</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Auto-Settled Records</div><div class='metric-value' style='color:#0284C7;'>{summary.get('reconciled_count', 0):,}</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Exceptions Flagged</div><div class='metric-value' style='color:#BE123C;'>{summary.get('exception_count', 0):,}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Financial AI Briefing Container
    formatted_ai_analysis = ai_analysis.replace(
        "#### Executive AI Audit Briefing & Risk Assessment", 
        "<h4 style='margin-top:0; color:#0F172A;'>Executive AI Audit Briefing & Risk Assessment</h4>"
    )

    st.markdown(f"""
    <div class='ai-card'>
        <h3 style='margin-top:0; color:#0F172A;'>Domain-Specific Financial AI Briefing (FinGPT)</h3>
        <hr style='border:none; border-top:1px solid rgba(203, 213, 225, 0.6); margin: 10px 0 15px 0;'>
        <div>{formatted_ai_analysis}</div>
    </div>
    """, unsafe_allow_html=True)

    # Data Visualizations
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Resolution Breakdown")
        pie_df = pd.DataFrame([
            {"Status": "Reconciled", "Count": summary.get('reconciled_count', 0)},
            {"Status": "Exceptions", "Count": summary.get('exception_count', 0)}
        ])
        fig_pie = px.pie(
            pie_df, values='Count', names='Status',
            color='Status',
            color_discrete_map={'Reconciled': '#0284C7', 'Exceptions': '#BE123C'},
            hole=0.45
        )
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#0F172A")
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        st.subheader("Exception Categories")
        if exceptions:
            df_exc_chart = pd.DataFrame(exceptions)
            issue_counts = df_exc_chart['issue'].value_counts().reset_index()
            issue_counts.columns = ['Category', 'Count']
            fig_bar = px.bar(
                issue_counts, x='Count', y='Category',
                orientation='h',
                color_discrete_sequence=['#BE123C']
            )
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#0F172A")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No exceptions detected in this dataset run.")

    st.markdown("---")

    # Detailed Audit Logs Table
    st.subheader("Transaction History & Exception Audit Log")
    
    view_mode = st.radio(
        "Select View Mode:",
        ["Flagged Exceptions Audit", "Auto-Settled Records"],
        horizontal=True
    )

    if view_mode == "Flagged Exceptions Audit":
        if exceptions:
            df_exc = pd.DataFrame(exceptions)
            
            filter_col1, filter_col2 = st.columns([3, 1])
            with filter_col1:
                search_query = st.text_input("Quick Search (Order ID / Record ID):", "", key="search_exc")
            with filter_col2:
                severity_filter = st.selectbox("Severity Level:", ["All", "High", "Medium"], key="sev_filter")

            if search_query:
                df_exc = df_exc[
                    df_exc['order_id'].astype(str).str.contains(search_query, case=False) |
                    df_exc['record_id'].astype(str).str.contains(search_query, case=False)
                ]
            
            if severity_filter != "All":
                df_exc = df_exc[df_exc['severity'] == severity_filter]

            st.dataframe(
                df_exc[['record_id', 'order_id', 'paid_amount', 'fee', 'issue', 'severity', 'action']],
                column_config={
                    "record_id": "Payment ID",
                    "order_id": "Order ID",
                    "paid_amount": st.column_config.NumberColumn("Amount Paid", format="₹%.2f"),
                    "fee": st.column_config.NumberColumn("Fee", format="₹%.2f"),
                    "issue": "Audit Exception Reason",
                    "severity": "Severity",
                    "action": "Resolution Status"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("Zero exceptions found in this batch.")

    else:
        if reconciled:
            df_rec = pd.DataFrame(reconciled)
            search_rec = st.text_input("Quick Search (Order ID / Record ID):", "", key="search_rec")
            
            if search_rec:
                df_rec = df_rec[
                    df_rec['order_id'].astype(str).str.contains(search_rec, case=False) |
                    df_rec['record_id'].astype(str).str.contains(search_rec, case=False)
                ]

            st.dataframe(
                df_rec[['record_id', 'order_id', 'amount', 'fee', 'status', 'confidence_score']],
                column_config={
                    "record_id": "Payment ID",
                    "order_id": "Order ID",
                    "amount": st.column_config.NumberColumn("Amount Paid", format="₹%.2f"),
                    "fee": st.column_config.NumberColumn("Fee", format="₹%.2f"),
                    "status": "Settlement Status",
                    "confidence_score": st.column_config.NumberColumn("Confidence", format="%.2f")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No reconciled records found.")

except Exception as e:
    st.error("Engine report missing. Click 'Execute Settlement Engine' in the left sidebar to generate.")
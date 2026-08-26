The **AI-Powered Financial Reconciliation Engine** is an enterprise settlement validation platform targeting fintech 
companies processing e-commerce payment gateways across Credit Cards, NEFT, and EMI. Built to resolve unmatched ledgers
and fee discrepancies using real-world Kaggle transaction datasets (`orders.csv`, `payments.csv`), the project features 
a hybrid high-level system architecture: `reconcile.py` executes sub-second O(N) vectorized matching (LLD) using **Pandas** 
and **NumPy**, while complex exceptions are routed to Hugging Face's **FinGPT 7B** model for automated risk assessment and 
mitigation guidance. The system displays real-time exception insights via a **Streamlit** dashboard (`app.py`) and exports 
structured audit logs (`reconciliation_report.json`).

###Tech Stack

-  **Language & Interface:** Python, Streamlit 
-  **Core Logic & LLD:** Pandas, NumPy
-  **AI Model:** Hugging Face Transformers (`FinGPT/fingpt-forecaster_dow30_llama2-7b_lora`)
-  **Data & Output Formats:** Kaggle CSV Datasets , JSON Audit Reports

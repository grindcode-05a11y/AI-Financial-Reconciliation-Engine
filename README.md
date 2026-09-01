# **AI-Financial-Reconciliation-Engine**

Payment reconciliation engine for e-commerce settlement validation — built
for Razorpay's AI Buildathon 2026 (Track 04, AI Finance Controller).

## **What it does**

Matches an orders ledger against a payment-gateway settlement file, and
reports what settled, what didn't, why, how severe each exception is, and
what should happen next.

## **System Architecture**

1. **Deterministic matching** — rule-based order/payment join with
   amount-tolerance and gateway-status checks. Decides reconciled vs.
   exception; fully auditable, no black-box decision over real money.
   Validated as base proof for the ledger engine using a synthetic
   100K+-order Indian e-commerce dataset from Kaggle
   *"Synthetic 100K-order Indian e-commerce dataset for sales, customer
   & ML analytics" — as described by Kaggle"*. A control panel is
   included to upload a custom dataset in CSV format for real-time
   results on real data.
2. **ML anomaly scoring** — unsupervised IsolationForest (scikit-learn)
   scores every transaction 0–100 for statistical unusualness. Runs
   in-process; no transaction data leaves the environment.
3. **Exception Resolution Agent** — routes each exception to one of five
   bounded actions (auto-retry, escalate to treasury, await refund
   confirmation, route to finance audit, standard review), with a logged
   reason per decision.

### Tech Stack
* **Language:** Python
* **UI Framework:** Streamlit
* **Data Processing:** Pandas & NumPy
* **Machine Learning:** Scikit-Learn (IsolationForest)
* **Visualizations:** Plotly

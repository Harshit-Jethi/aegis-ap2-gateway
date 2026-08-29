# Aegis-AP2 Enterprise Gateway
### Bounded & Gated Agentic Commerce Platform on Razorpay Rails
**Track 01: AI Growth & Agentic Commerce | Razorpay Integration Protocol**

---

## 1. Problem Statement & Core Value Proposition
Large Language Models (LLMs) are probabilistic and vulnerable to hallucinated pricing, prompt injection, and race conditions during network retries. Giving an LLM direct API access to create or authorize payment transactions introduces critical financial vulnerabilities.

**Aegis-AP2** resolves this through a **Zero-Trust 3-Tier Air-Gap Architecture**:
* **Autonomous Intelligence Layer:** Agents reason, compare specifications, and formulate purchase intents, but have **zero direct execution authority or payment credentials**.
* **Deterministic Financial Gating Layer:** Six strict algorithmic rules evaluate intents against authoritative catalog state, ceiling limits, stock availability, and idempotency signatures before minting an HMAC-SHA256 `SpendPermit`.
* **Settlement Rails:** Razorpay Orders API (`POST /v1/orders`) is triggered with integer paise precision, customer checkout is rendered via native modal (`checkout.js`), and transactions are finalized via constant-time HMAC-SHA256 verified webhooks.

---

## 2. Dual-Mode Architecture


┌────────────────────────────────────────────────────────┐
                           │                 UNTRUSTED AI LAYER                     │
                           ├──────────────────────────┬─────────────────────────────┤
                           │  MODE 1: A2A SWARM       │  MODE 2: COPILOT & MODAL    │
                           │  • Buyer ReAct Agent     │  • Interactive Shopping Chat│
                           │  • Seller Revenue Agent  │  • Spec Comparison Copilot  │
                           │  • Red-Team Sentinel     │  • Intent Formulation       │
                           └────────────┬─────────────┴──────────────┬──────────────┘
                                        │                            │
                                        └─────────────┬──────────────┘
                                                      │ (ProposedOrderIntent JSON)
                                                      ▼
                           ┌────────────────────────────────────────────────────────┐
                           │           DETERMINISTIC GATING LAYER                   │
                           │           (backend/app/policy_engine.py)               │
                           ├────────────────────────────────────────────────────────┤
                           │  [Check 1] Circuit Breaker (Max Session Retries)       │
                           │  [Check 2] Authoritative Price Match (Catalog Truth)   │
                           │  [Check 3] Real-Time Stock & Warehouse Lock            │
                           │  [Check 4] Bounded Ceiling Guard (<= ₹15,000 INR)      │
                           │  [Check 5] Explicit User Confirmation Gate             │
                           │  [Check 6] SHA-256 Idempotency Hash (Replay Defense)   │
                           └──────────────────────────┬─────────────────────────────┘
                                                      │ (HMAC-SHA256 SpendPermit)
                                                      ▼
                           ┌────────────────────────────────────────────────────────┐
                           │            RAZORPAY TEST SETTLEMENT RAILS              │
                           ├────────────────────────────────────────────────────────┤
                           │  • Backend Orders API: POST /v1/orders (Integer Paise) │
                           │  • Client Modal: Razorpay Standard Checkout SDK        │
                           │  • Webhook Verification: HMAC-SHA256 (order.paid)      │
                           └──────────────────────────┬─────────────────────────────┘
                                                      │
                                                      ▼
                           ┌────────────────────────────────────────────────────────┐
                           │            APPEND-ONLY IMMUTABLE AUDIT TRAIL           │
                           │            (backend/data/audit_ledger.jsonl)           │
                           └────────────────────────────────────────────────────────┘



### Mode 1: Autonomous Agent-to-Agent (A2A) Cognitive Swarm
* **AI Buyer Agent:** Ingests high-level business mandates and selects optimal baseline hardware.
* **AI Merchant Revenue Optimizer:** Evaluates pricing elasticity and dynamically proposes complementary accessories, boosting **Merchant GMV by +43.6%**.
* **Adversarial Sentinel:** Validates the negotiation transcript against prompt injection and price manipulation before submitting intents.
* **Telemetry Stream:** Streams multi-agent cognitive reasoning packets to the client via Server-Sent Events (SSE).

### Mode 2: Conversational Copilot & Standard Razorpay Modal
* **Interactive Shopping Assistant:** Natural language search, recommendation, and intent formulation.
* **Native Modal Mount:** Injects and opens Razorpay's native checkout overlay on SpendPermit authorization.
* **Graceful Failure Recovery:** Catches test card declines, logs recoverable state in the audit trail, preserves cart contents, and prompts the user to retry without causing double-billing.

---

## 3. Project Directory Structure

```text
aegis-acp-gateway/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py             # Environment configurations and safety ceilings
│   │   ├── models.py             # Pydantic data schemas (Intents, Permits, Events)
│   │   ├── agent.py              # Conversational shopping agent with tool isolation
│   │   ├── agent_kernel.py       # Tri-Agent A2A Swarm orchestrator
│   │   ├── policy_engine.py      # 6 deterministic gating checks & SpendPermit minting
│   │   ├── razorpay_client.py    # Razorpay SDK client & constant-time HMAC verifier
│   │   ├── audit_logger.py       # Append-only synchronous JSON-L event logger
│   │   └── main.py               # FastAPI routes & webhook listener
│   ├── data/
│   │   ├── catalog.json          # Authoritative merchant product inventory
│   │   └── audit_ledger.jsonl    # Immutable audit ledger records
│   ├── .env                      # Local secrets (Razorpay keys, Gemini key)
│   ├── .env.example              # Sanitized environment template
│   └── requirements.txt          # Python backend dependencies
├── frontend/
│   ├── index.html                # HTML entry point loading Razorpay Checkout script
│   ├── src/
│   │   ├── app.jsx               # Dual-Mode Cockpit & Audit Inspector UI
│   │   ├── main.jsx              # React mounting root
│   │   └── index.css             # Tailwind CSS styles
│   ├── package.json              # Frontend scripts and UI icons
│   └── vite.config.js            # Vite configuration
└── README.md                     # Architecture specification & evaluation guide


4. Setup and Installation
Prerequisites
Python 3.10+

Node.js 18+ & npm

Razorpay Test Mode account credentials

Backend Setup
Open a PowerShell terminal in the backend directory:

PowerShell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Create and configure backend/.env:

Code snippet
RAZORPAY_KEY_ID=rzp_test_TTB0EsaAYGofS0
RAZORPAY_KEY_SECRET=gJce4Ab90KDLv5VP2stnvh0X
RAZORPAY_WEBHOOK_SECRET=aegis_webhook_secret_2026
GEMINI_API_KEY=your_gemini_api_key_here
MAX_ORDER_VALUE_INR=15000.0
MAX_RETRY_LIMIT=10
Run the FastAPI development server:

PowerShell
uvicorn app.main:app --reload --port 8000
Frontend Setup
Open a new PowerShell terminal in the frontend directory:

PowerShell
cd frontend
npm install
npm run dev
Access the application at http://localhost:5173.

Webhook Tunneling (Razorpay Dashboard)
In VS Code, navigate to the Ports tab → Forward port 8000 → Set Port Visibility to Public.

Copy the generated HTTPS endpoint URL (e.g., https://xxxx-8000.inc1.devtunnels.ms).

In Razorpay Dashboard (Test Mode) → Account & Settings → Webhooks → Add New Webhook:

Webhook URL: https://<your-tunnel-url>/api/webhooks/razorpay

Secret: aegis_webhook_secret_2026

Active Events: order.paid, payment.failed

5. Live Demonstration & Evaluation Test Cases
Scenario	Actions to Perform	Verification Points
1. Autonomous A2A Negotiation (Mode 1)	Select Mode 1. Set mandate: "Equip workspace under ₹11,000". Click Dispatch Autonomous Negotiation Swarm.	Observe live token packets: Buyer picks Monitor (₹5,500), Seller bundles Keyboard (+43.6% GMV to ₹7,900), Sentinel verifies constraints, Gate mints permit and settles on Razorpay rails.
2. Conversational Modal Checkout (Mode 2)	Select Mode 2. Message: "I want to buy the Low-Profile Mechanical Keyboard". Click Confirm & Pay (Modal).	Intent formulated → Deterministic gate evaluates checks → Mounts standard Razorpay modal → Complete using test UPI or card.
3. Stockout Chaos Defense	In the top-right catalog, click Chaos: 0 on HW-MECH-KEYBOARD-RGB. Click Confirm & Pay.	Gate halts execution with ERR_INSUFFICIENT_STOCK. Order creation blocked. Audit ledger logs GATE_REJECTED in red.
4. Payment Decline Recovery	Reset stock to 10. Click Confirm & Pay. In Razorpay modal, select Card and simulate Failure / Decline.	Modal intercepts decline → Agent delivers natural language recovery guidance → Audit logs PAYMENT_DECLINED_RECOVERABLE → Cart state preserved for retry.
5. Cryptographic Webhook Inspection	Open the Immutable Audit Ledger in the right column and select any log entry.	Inspect JSON-L structure showing Trace ID, timestamps, HMAC SpendPermit signature, and verified Razorpay webhook payloads.
6. Financial Safety & Security Invariants
Integer Math in Paise: All transactions are converted to integer paise (int(amount * 100)) prior to API dispatch, preventing floating-point rounding errors.

Authoritative Source of Truth: Item prices and inventory counts are resolved directly from catalog.json. Price parameters provided by the LLM are treated as untrusted claims.

Constant-Time Verification: Webhook signatures are validated using hmac.compare_digest() to eliminate timing side-channel attacks.

Append-Only Immutability: Audit records are written synchronously with thread-level locks to audit_ledger.jsonl, preventing state overwrites or transaction history tampering.

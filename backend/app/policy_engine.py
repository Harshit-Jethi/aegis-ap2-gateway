import json
import hmac
import hashlib
import time
import os
from typing import Dict, Any, Tuple, Optional, Set
from app.config import settings
from app.models import ProposedOrderIntent, GateEvaluationResult

CATALOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "catalog.json"))

class DeterministicPolicyEngine:
    def __init__(self):
        self.secret_key = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        self.max_order_limit = settings.MAX_ORDER_VALUE_INR
        self.max_retry_limit = 10  # Increased threshold for interactive testing
        
        self._idempotency_cache: Dict[str, Dict[str, Any]] = {}
        self._session_attempts: Dict[str, int] = {}

    def _read_catalog(self) -> list:
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def compute_idempotency_key(self, session_id: str, sku: str, quantity: int) -> str:
        raw_seed = f"{session_id}:{sku}:{quantity}:{int(time.time() // 60)}"
        return hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:24]

    def evaluate_intent(self, intent: ProposedOrderIntent) -> GateEvaluationResult:
        catalog = self._read_catalog()
        session_id = intent.session_id
        
        # GATE 1: Circuit Breaker / Retry Limiter
        attempts = self._session_attempts.get(session_id, 0) + 1
        self._session_attempts[session_id] = attempts
        
        if attempts > self.max_retry_limit:
            return GateEvaluationResult(
                approved=False,
                status_code="ERR_RETRY_LIMIT_EXCEEDED",
                reason=f"Session exceeded maximum retry limit ({self.max_retry_limit}). Payment locked.",
                authorized_amount_inr=0.0,
                authorized_amount_paise=0,
                idempotency_key=""
            )

        # GATE 2: Authoritative Catalog Price Reconciliation
        catalog_item = next((item for item in catalog if item["sku"].upper() == intent.sku.upper()), None)
        if not catalog_item:
            return GateEvaluationResult(
                approved=False,
                status_code="ERR_UNKNOWN_SKU",
                reason=f"SKU '{intent.sku}' does not exist in authoritative merchant catalog.",
                authorized_amount_inr=0.0,
                authorized_amount_paise=0,
                idempotency_key=""
            )

        real_unit_price = float(catalog_item["price_inr"])
        claimed_unit_price = float(intent.claimed_unit_price_inr)
        
        if abs(real_unit_price - claimed_unit_price) > 0.01:
            return GateEvaluationResult(
                approved=False,
                status_code="ERR_PRICE_TAMPERING_DETECTED",
                reason=f"Price mismatch: Claimed ₹{claimed_unit_price:,.2f} vs Catalog ₹{real_unit_price:,.2f}.",
                authorized_amount_inr=0.0,
                authorized_amount_paise=0,
                idempotency_key=""
            )

        # GATE 3: Real-Time Stock Verification
        current_stock = int(catalog_item.get("stock_quantity", 0))
        if current_stock < intent.quantity:
            return GateEvaluationResult(
                approved=False,
                status_code="ERR_INSUFFICIENT_STOCK",
                reason=f"Insufficient inventory: Requested {intent.quantity} units, but only {current_stock} in stock.",
                authorized_amount_inr=0.0,
                authorized_amount_paise=0,
                idempotency_key=""
            )

        # GATE 4: Bounded Limit Ceiling Check
        total_authorized_inr = round(real_unit_price * intent.quantity, 2)
        if total_authorized_inr > self.max_order_limit:
            return GateEvaluationResult(
                approved=False,
                status_code="ERR_ORDER_CEILING_EXCEEDED",
                reason=f"Order total ₹{total_authorized_inr:,.2f} exceeds ceiling of ₹{self.max_order_limit:,.2f}.",
                authorized_amount_inr=0.0,
                authorized_amount_paise=0,
                idempotency_key=""
            )

        # GATE 5: Explicit User Confirmation Guard
        if not intent.confirmed_by_user:
            return GateEvaluationResult(
                approved=False,
                status_code="ERR_AWAITING_USER_CONFIRMATION",
                reason="Explicit user confirmation missing.",
                authorized_amount_inr=total_authorized_inr,
                authorized_amount_paise=int(total_authorized_inr * 100),
                idempotency_key=""
            )

        # SUCCESS: Mint Cryptographic Permit
        idempotency_key = self.compute_idempotency_key(session_id, intent.sku, intent.quantity)
        total_paise = int(total_authorized_inr * 100)
        signature_payload = f"{idempotency_key}:{intent.sku}:{total_paise}:{int(time.time())}"
        crypto_signature = hmac.new(
            self.secret_key, 
            signature_payload.encode("utf-8"), 
            hashlib.sha256
        ).hexdigest()

        return GateEvaluationResult(
            approved=True,
            status_code="PERMIT_GRANTED",
            reason="All deterministic guardrails verified. SpendPermit minted.",
            authorized_amount_inr=total_authorized_inr,
            authorized_amount_paise=total_paise,
            idempotency_key=idempotency_key,
            cryptographic_signature=crypto_signature
        )

policy_engine = DeterministicPolicyEngine()
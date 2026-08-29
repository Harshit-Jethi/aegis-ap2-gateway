import hmac
import hashlib
import time
import uuid
from typing import Dict, Any, Tuple, Optional
from app.config import settings

class HTTP402ProtocolEngine:
    def __init__(self):
        self.used_nonces = set()
        secret = settings.RAZORPAY_KEY_SECRET if hasattr(settings, "RAZORPAY_KEY_SECRET") and settings.RAZORPAY_KEY_SECRET else "dev_secret_key"
        self.secret_key = secret.encode("utf-8")

    def generate_payment_challenge(self, sku: str, base_price: float, upsell_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        nonce = f"nonce_{uuid.uuid4().hex[:16]}_{int(time.time())}"
        amount = upsell_data["bundle_price"] if upsell_data else base_price
        
        raw_payload = f"{nonce}:{sku}:{amount:.2f}"
        challenge_signature = hmac.new(self.secret_key, raw_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        
        return {
            "status_code": 402,
            "status_message": "Payment Required (AP2/x402 Standard)",
            "challenge": {
                "nonce": nonce,
                "target_sku": sku,
                "amount_inr": amount,
                "currency": "INR",
                "challenge_hash": challenge_signature,
                "expiry_epoch": int(time.time()) + 180,
                "merchant_id": "merchant_rzp_001",
                "upsell_payload": upsell_data
            }
        }

    def verify_and_settle(self, signed_challenge: Dict[str, Any], user_max_budget: float) -> Tuple[bool, str, Dict[str, Any]]:
        nonce = signed_challenge.get("nonce")
        amount = float(signed_challenge.get("amount_inr", 0.0))
        sku = signed_challenge.get("target_sku", "")
        sig = signed_challenge.get("challenge_hash", "")
        
        if nonce in self.used_nonces:
            return False, "ERR_REPLAY_ATTACK_DETECTED: Nonce already consumed.", {}
        
        if amount > user_max_budget:
            return False, f"ERR_BUDGET_OVERRUN: Amount ₹{amount} exceeds limit of ₹{user_max_budget}.", {}

        expected_payload = f"{nonce}:{sku}:{amount:.2f}"
        expected_sig = hmac.new(self.secret_key, expected_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(sig, expected_sig):
            return False, "ERR_CRYPTO_SIGNATURE_MISMATCH: Signature check failed.", {}

        self.used_nonces.add(nonce)
        permit_id = f"permit_{uuid.uuid4().hex[:12]}"
        return True, "AP2_SETTLEMENT_VERIFIED", {
            "permit_id": permit_id,
            "authorized_amount": amount,
            "nonce": nonce,
            "status": "READY_FOR_RAZORPAY_SETTLEMENT"
        }

protocol_engine = HTTP402ProtocolEngine()
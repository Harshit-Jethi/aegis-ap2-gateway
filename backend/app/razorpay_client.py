import razorpay
import hmac
import hashlib
import uuid
from typing import Dict, Any, Tuple, Optional
from app.config import settings
from app.models import GateEvaluationResult, SpendPermit, ExecutionResult

class RazorpayExecutionGateway:
    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        
        # Initialize official Razorpay SDK client
        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def create_order(self, permit: GateEvaluationResult) -> ExecutionResult:
        """
        Calls Razorpay Orders API (/v1/orders) to generate a test-mode order.
        Only executed after SpendPermit validation.
        """
        audit_id = f"trace_{uuid.uuid4().hex[:10]}"
        receipt_id = f"rcpt_{permit.idempotency_key[:12]}"
        
        if not permit.approved:
            return ExecutionResult(
                order_id=None,
                payment_status="REJECTED_BY_GATE",
                amount_paid_inr=0.0,
                currency="INR",
                razorpay_receipt=receipt_id,
                audit_trace_id=audit_id,
                error_message=permit.reason
            )

        try:
            order_payload = {
                "amount": permit.authorized_amount_paise,
                "currency": "INR",
                "receipt": receipt_id,
                "notes": {
                    "idempotency_key": permit.idempotency_key,
                    "audit_trace_id": audit_id,
                    "gate_status": permit.status_code
                }
            }

            # Server-to-server call to Razorpay Orders API
            rzp_order = self.client.order.create(data=order_payload)
            
            return ExecutionResult(
                order_id=rzp_order["id"],
                payment_status="ORDER_CREATED_TEST_MODE",
                amount_paid_inr=permit.authorized_amount_inr,
                currency="INR",
                razorpay_receipt=receipt_id,
                audit_trace_id=audit_id
            )

        except Exception as e:
            return ExecutionResult(
                order_id=None,
                payment_status="RAZORPAY_API_ERROR",
                amount_paid_inr=0.0,
                currency="INR",
                razorpay_receipt=receipt_id,
                audit_trace_id=audit_id,
                error_message=str(e)
            )

    def execute_order(self, permit: SpendPermit) -> ExecutionResult:
        """Legacy compatibility adapter for protocol engine calls."""
        gate_equiv = GateEvaluationResult(
            approved=permit.approved,
            status_code=permit.status_code,
            reason=permit.reason,
            authorized_amount_inr=permit.authorized_amount_inr,
            authorized_amount_paise=int(permit.authorized_amount_inr * 100),
            idempotency_key=permit.idempotency_key or f"idem_{uuid.uuid4().hex[:12]}"
        )
        return self.create_order(gate_equiv)

    def verify_webhook_signature(self, raw_body: bytes, received_signature: str) -> Tuple[bool, str]:
        """
        Cryptographically verifies the incoming Razorpay webhook signature using HMAC-SHA256.
        Uses constant-time comparison to prevent timing side-channel attacks.
        """
        if not received_signature:
            return False, "ERR_MISSING_SIGNATURE"

        generated_signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(generated_signature, received_signature):
            return True, "SIGNATURE_VALIDATED"
        else:
            return False, "ERR_INVALID_WEBHOOK_SIGNATURE"

razorpay_gateway = RazorpayExecutionGateway()
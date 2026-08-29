from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CatalogItem(BaseModel):
    sku: str
    name: str
    category: str
    price_inr: float
    stock_quantity: int
    description: str
    merchant_id: str

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", or "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ProposedOrderIntent(BaseModel):
    intent_id: str
    session_id: str
    sku: str
    item_name: str
    quantity: int = 1
    claimed_unit_price_inr: float
    confirmed_by_user: bool = False
    reasoning: str

class TransactionIntent(BaseModel):
    intent_id: str
    buyer_agent_id: str
    merchant_id: str
    sku: str
    quantity: int = 1
    target_unit_price_inr: float
    total_expected_cost_inr: float
    reasoning_trace: str

class SpendPermit(BaseModel):
    permit_id: str
    intent_id: str
    approved: bool
    status_code: str  # e.g., "PERMIT_GRANTED", "ERR_INSUFFICIENT_STOCK"
    reason: str
    authorized_amount_inr: float
    authorized_amount_paise: Optional[int] = None
    cryptographic_signature: Optional[str] = None
    idempotency_key: Optional[str] = None

class GateEvaluationResult(BaseModel):
    approved: bool
    status_code: str
    reason: str
    authorized_amount_inr: float
    authorized_amount_paise: int
    idempotency_key: str
    cryptographic_signature: Optional[str] = None

class ExecutionResult(BaseModel):
    order_id: Optional[str] = None
    payment_status: str
    amount_paid_inr: float
    currency: str = "INR"
    razorpay_receipt: str
    audit_trace_id: str
    error_message: Optional[str] = None

class RazorpayOrderPayload(BaseModel):
    order_id: Optional[str] = None
    amount_inr: float
    amount_paise: int
    currency: str = "INR"
    receipt: str
    status: str
    payment_link: Optional[str] = None

class AuditEvent(BaseModel):
    timestamp: str
    session_id: Optional[str] = None
    event_type: str
    payload: Dict[str, Any]
    gate_decision: Optional[str] = None
    order_id: Optional[str] = None
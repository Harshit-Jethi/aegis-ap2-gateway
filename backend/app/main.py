import json
import traceback
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.models import ProposedOrderIntent, GateEvaluationResult
from app.policy_engine import policy_engine
from app.razorpay_client import razorpay_gateway
from app.audit_logger import audit_logger
from app.agent_kernel import agent_kernel
from app.agent import checkout_agent

app = FastAPI(
    title="Aegis-AP2 Dual-Mode Enterprise Gateway",
    description="Dual-Mode Agentic Commerce Gateway (A2A Swarm + Conversational Checkout) on Razorpay Rails",
    version="6.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    chat_history: List[Dict[str, str]] = []
    session_id: str = "session_dev_001"

class OrderConfirmationRequest(BaseModel):
    intent: ProposedOrderIntent

class PaymentFailureRequest(BaseModel):
    session_id: str
    order_id: Optional[str] = None
    error_code: str
    error_description: str
    sku: str

class ChaosStockRequest(BaseModel):
    sku: str
    new_stock: int

class StreamProcureRequest(BaseModel):
    user_goal: str
    max_budget: float = 12000.0

# -----------------------------------------------------------------------------
# General System Endpoints
# -----------------------------------------------------------------------------
@app.get("/")
def health():
    return {
        "status": "online",
        "system": "Aegis-AP2 Dual-Mode Gateway",
        "modes": ["A2A_COGNITIVE_SWARM", "CONVERSATIONAL_CHECKOUT_COPILOT"],
        "rails": "Razorpay Test Rails"
    }

@app.get("/api/catalog")
def get_catalog():
    with open("data/catalog.json", "r") as f:
        return json.load(f)

@app.get("/api/audit-ledger")
def get_audit_ledger():
    return audit_logger.get_recent_logs(limit=30)

@app.post("/api/chaos/set-stock")
def set_sku_stock(req: ChaosStockRequest):
    with open("data/catalog.json", "r") as f:
        catalog = json.load(f)
        
    for item in catalog:
        if item["sku"] == req.sku:
            item["stock_quantity"] = req.new_stock
            break
            
    with open("data/catalog.json", "w") as f:
        json.dump(catalog, f, indent=2)
        
    return {"message": f"Updated stock of {req.sku} to {req.new_stock}"}

# -----------------------------------------------------------------------------
# MODE 1 ENDPOINT: Autonomous A2A Cognitive Swarm (SSE Token Stream)
# -----------------------------------------------------------------------------
@app.post("/api/protocol/stream")
def stream_protocol(req: StreamProcureRequest):
    def event_generator():
        for packet in agent_kernel.stream_protocol_exchange(req.user_goal, req.max_budget):
            yield f"data: {packet}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# -----------------------------------------------------------------------------
# MODE 2 ENDPOINTS: Conversational Copilot & Interactive Modal
# -----------------------------------------------------------------------------
@app.post("/api/chat")
def process_chat_message(req: ChatRequest):
    result = checkout_agent.process_message(
        user_message=req.message,
        chat_history=req.chat_history,
        session_id=req.session_id
    )
    return result

@app.post("/api/orders/confirm-and-create")
def confirm_and_create_order(req: OrderConfirmationRequest):
    try:
        # Deterministic Gate Verification
        gate_result: GateEvaluationResult = policy_engine.evaluate_intent(req.intent)
        
        # Razorpay Test Order Generation
        execution = razorpay_gateway.create_order(gate_result)
        
        # Immutable Audit Record
        event_type = "ORDER_MINTED_SUCCESS" if gate_result.approved and execution.order_id else "GATE_REJECTED"
        audit_logger.log_event(
            event_type=event_type,
            goal=req.intent.reasoning,
            intent_payload=req.intent.model_dump(mode="json"),
            permit_payload=gate_result.model_dump(mode="json"),
            execution_payload=execution.model_dump(mode="json")
        )
        
        return {
            "gate_result": gate_result.model_dump(mode="json"),
            "execution": execution.model_dump(mode="json"),
            "key_id": razorpay_gateway.key_id
        }
    except Exception as err:
        print("❌ Error in confirm-and-create:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(err))

@app.post("/api/orders/handle-failure")
def handle_payment_failure(req: PaymentFailureRequest):
    audit_logger.log_event(
        event_type="PAYMENT_DECLINED_RECOVERABLE",
        goal=f"Modal Payment Failure for Order {req.order_id or 'UNKNOWN'}",
        intent_payload={
            "session_id": req.session_id,
            "sku": req.sku,
            "status": "PAYMENT_FAILED_RETRYABLE"
        },
        permit_payload={
            "error_code": req.error_code,
            "error_description": req.error_description
        },
        execution_payload={
            "order_id": req.order_id,
            "recovery_state": "ACTIVE"
        }
    )

    recovery_msg = (
        f"Your test payment could not be processed ({req.error_description}). "
        f"No funds were deducted, and your cart is preserved. You can safely retry whenever ready."
    )

    return {
        "status": "RECOVERY_ACTIVE",
        "recovery_message": recovery_msg,
        "retry_permitted": True
    }

# -----------------------------------------------------------------------------
# SERVER-SIDE WEBHOOK LISTENER (HMAC-SHA256 Authenticated)
# -----------------------------------------------------------------------------
@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None)
):
    raw_body = await request.body()
    
    is_valid, msg = razorpay_gateway.verify_webhook_signature(raw_body, x_razorpay_signature or "")
    if not is_valid:
        print(f"⚠️ Webhook Security Alert: {msg}")
        audit_logger.log_event(
            event_type="SECURITY_ALERT_INVALID_WEBHOOK_SIGNATURE",
            goal="Webhook HMAC Check",
            intent_payload={"error": msg},
            permit_payload={},
            execution_payload={"raw_signature": x_razorpay_signature}
        )
        raise HTTPException(status_code=400, detail=msg)

    payload = json.loads(raw_body.decode("utf-8"))
    event = payload.get("event")
    event_data = payload.get("payload", {})
    
    order_id = None
    if "order" in event_data:
        order_id = event_data["order"]["entity"]["id"]
    elif "payment" in event_data:
        order_id = event_data["payment"]["entity"].get("order_id")

    audit_logger.log_event(
        event_type=f"WEBHOOK_{event.upper().replace('.', '_')}",
        goal=f"Asynchronous Razorpay Event: {event}",
        intent_payload={"event": event, "order_id": order_id},
        permit_payload={"signature_verified": True},
        execution_payload=event_data
    )

    return {"status": "ok", "event_processed": event}
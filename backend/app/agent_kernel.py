import json
import time
import uuid
import os
from typing import Generator
from app.ai_agents import ai_swarm
from app.protocol_402 import protocol_engine
from app.razorpay_client import razorpay_gateway
from app.models import SpendPermit
from app.audit_logger import audit_logger

class AutonomousCommerceKernel:
    def stream_protocol_exchange(self, goal: str, max_budget: float = 12000.0) -> Generator[str, None, None]:
        session_id = f"ap2_{uuid.uuid4().hex[:8]}"

        # =====================================================================
        # PHASE 1: AGENT 1 (AI BUYER) — Live LLM Chain-of-Thought
        # =====================================================================
        buyer_res = ai_swarm.run_buyer_agent(goal, max_budget)
        yield json.dumps({
            "event": "AGENT_THOUGHT",
            "frame": 1,
            "layer": "BUYER_COGNITIVE_REASONING",
            "sender": "Agent 1: AI Buyer (Gemini 2.5 Flash)",
            "payload": {
                "chain_of_thought": buyer_res.get("thought_process"),
                "selected_sku": buyer_res.get("selected_sku"),
                "rfq_dispatch": buyer_res.get("rfq_message")
            }
        })
        time.sleep(0.4)

        # =====================================================================
        # PHASE 2: AGENT 2 (AI SELLER) — Live Dynamic Revenue Optimization
        # =====================================================================
        seller_res = ai_swarm.run_seller_agent(buyer_res, max_budget)
        yield json.dumps({
            "event": "AGENT_PROPOSAL",
            "frame": 2,
            "layer": "SELLER_REVENUE_OPTIMIZER",
            "sender": "Agent 2: AI Merchant Optimizer (Gemini 2.5 Flash)",
            "payload": {
                "revenue_strategy": seller_res.get("revenue_strategy"),
                "final_offer": seller_res.get("counter_offer_proposal"),
                "settlement_price_inr": seller_res.get("total_settlement_price_inr"),
                "gmv_expansion": seller_res.get("merchant_gmv_growth_pct")
            }
        })
        time.sleep(0.4)

        # =====================================================================
        # PHASE 3: AGENT 3 (AI SECURITY SENTINEL) — Red-Team Adversarial Audit
        # =====================================================================
        sentinel_res = ai_swarm.run_security_sentinel(buyer_res, seller_res, max_budget)
        verdict = sentinel_res.get("security_verdict", "PASSED")
        
        yield json.dumps({
            "event": "SECURITY_AUDIT",
            "frame": 3,
            "layer": "AI_RED_TEAM_SENTINEL",
            "sender": "Agent 3: Adversarial AI Sentinel (Gemini 2.5 Flash)",
            "payload": {
                "verdict": verdict,
                "confidence_score": sentinel_res.get("confidence_score"),
                "threat_analysis": sentinel_res.get("threat_vector_analysis"),
                "audit_flags": sentinel_res.get("audit_flags")
            }
        })
        time.sleep(0.3)

        if verdict != "PASSED":
            yield json.dumps({
                "event": "SECURITY_HALT",
                "frame": 4,
                "layer": "GATEWAY_TERMINATED",
                "sender": "Deterministic Isolation Layer",
                "payload": {"error": "TERMINATED_BY_AI_SENTINEL", "detail": sentinel_res}
            })
            return

        # =====================================================================
        # PHASE 4: DETERMINISTIC PROTOCOL GATE & CRYPTOGRAPHIC MINT
        # =====================================================================
        final_price = float(seller_res.get("total_settlement_price_inr", 5500.0))
        target_sku = buyer_res.get("selected_sku", "HW-DEV-MONITOR-4K")
        
        challenge = protocol_engine.generate_payment_challenge(
            sku=target_sku,
            base_price=final_price
        )

        is_valid, reason, permit_data = protocol_engine.verify_and_settle(challenge["challenge"], max_budget)
        if not is_valid:
            yield json.dumps({
                "event": "POLICY_REJECT",
                "frame": 4,
                "layer": "GUARDRAIL_INTERCEPT",
                "sender": "Deterministic Policy Engine",
                "payload": {"error": reason}
            })
            return

        yield json.dumps({
            "event": "SPEND_PERMIT_MINTED",
            "frame": 4,
            "layer": "HMAC_SHA256_PERMIT",
            "sender": "Deterministic Policy Gate",
            "payload": permit_data
        })
        time.sleep(0.3)

        # =====================================================================
        # PHASE 5: RAZORPAY TEST-MODE SETTLEMENT & AUDIT PROOF
        # =====================================================================
        dummy_permit = SpendPermit(
            permit_id=permit_data["permit_id"],
            intent_id=session_id,
            approved=True,
            status_code="PERMIT_GRANTED",
            reason="Multi-Agent AI Consensus & Cryptographic Invariants Verified",
            authorized_amount_inr=permit_data["authorized_amount"],
            cryptographic_signature=challenge["challenge"]["challenge_hash"]
        )

        exec_res = razorpay_gateway.execute_order(dummy_permit)
    
        audit_logger.log_event(
            event_type="AI_SWARM_AP2_SETTLED",
            goal=goal,
            intent_payload={"buyer": buyer_res, "seller": seller_res},
            permit_payload=permit_data,
            execution_payload=exec_res.model_dump(mode="json")
        )

        yield json.dumps({
            "event": "PROTOCOL_COMPLETE",
            "frame": 5,
            "layer": "RAZORPAY_SETTLEMENT_RAILS",
            "sender": "Razorpay Orders API",
            "payload": {
                "order_id": exec_res.order_id,
                "amount_settled_inr": exec_res.amount_paid_inr,
                "status": "ORDER_CREATED_TEST_MODE",
                "receipt": exec_res.razorpay_receipt,
                "audit_trace_id": exec_res.audit_trace_id
            }
        })

agent_kernel = AutonomousCommerceKernel()
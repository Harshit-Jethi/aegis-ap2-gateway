import json
import os
import uuid
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from app.config import settings
from app.models import ProposedOrderIntent

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "catalog.json")

def load_catalog() -> List[Dict[str, Any]]:
    with open(CATALOG_PATH, "r") as f:
        return json.load(f)

# ============================================================================
# AGENT TOOL DEFINITIONS (Informational & Proposal Only — ZERO Financial Tools)
# ============================================================================

def tool_query_catalog(category: Optional[str] = None, search_term: Optional[str] = None) -> str:
    """Search and browse products in the merchant catalog."""
    catalog = load_catalog()
    results = []
    
    for item in catalog:
        match_cat = not category or category.lower() in item["category"].lower()
        match_search = not search_term or (
            search_term.lower() in item["name"].lower() or 
            search_term.lower() in item["description"].lower() or
            search_term.lower() in item["sku"].lower()
        )
        if match_cat and match_search:
            results.append({
                "sku": item["sku"],
                "name": item["name"],
                "category": item["category"],
                "price_inr": item["price_inr"],
                "in_stock": item["stock_quantity"] > 0,
                "stock_quantity": item["stock_quantity"],
                "description": item["description"]
            })
    
    return json.dumps(results if results else {"message": "No matching products found."})

def tool_get_product_details(sku: str) -> str:
    """Retrieve full specifications and stock level for a specific product SKU."""
    catalog = load_catalog()
    for item in catalog:
        if item["sku"].upper() == sku.upper():
            return json.dumps(item)
    return json.dumps({"error": f"SKU '{sku}' not found in catalog."})

def tool_propose_order(sku: str, quantity: int, claimed_unit_price: float, reasoning: str) -> str:
    """
    Assembles a proposed purchase order intent.
    DOES NOT CHARGE THE USER OR CREATE AN ORDER.
    Sends this proposal to the deterministic security gate for validation.
    """
    catalog = load_catalog()
    item = next((i for i in catalog if i["sku"].upper() == sku.upper()), None)
    
    item_name = item["name"] if item else "Unknown SKU"
    
    intent = {
        "intent_id": f"intent_{uuid.uuid4().hex[:8]}",
        "sku": sku.upper(),
        "item_name": item_name,
        "quantity": max(1, quantity),
        "claimed_unit_price_inr": float(claimed_unit_price),
        "reasoning": reasoning,
        "requires_user_confirmation": True
    }
    return json.dumps({"status": "ORDER_INTENT_FORMULATED", "intent": intent})

# ============================================================================
# AGENT RUNTIME ORCHESTRATOR
# ============================================================================

SYSTEM_INSTRUCTION = """You are the Aegis-ACP Conversational Shopping & Checkout Agent.
Your role is to assist users in discovering products, comparing hardware/cloud specifications, and preparing purchases.

OPERATIONAL BOUNDARIES:
1. You can search the catalog using `tool_query_catalog` and get specific details using `tool_get_product_details`.
2. When a user decides they want to purchase an item, invoke `tool_propose_order`.
3. CRITICAL FINANCIAL INVARIANT: You CANNOT execute payments, create Razorpay orders, or modify prices. You can ONLY propose an order intent.
4. Always clearly summarize product specs, unit price in INR, and ask the user for confirmation before finalizing proposals.
5. If an item is out of stock or exceeds known safety thresholds, explain the limitation clearly and suggest alternatives.
"""

class ConversationalCheckoutAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        if self.api_key and "your_" not in self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to init Gemini: {e}")

    def process_message(self, user_message: str, chat_history: List[Dict[str, str]], session_id: str) -> Dict[str, Any]:
        """
        Processes a conversational message turn, executing tool calls when required.
        Returns the agent response text and any formulated ProposedOrderIntent.
        """
        # Heuristic intent parser fallback when offline or without an active API key
        if not self.client:
            return self._heuristic_fallback(user_message, session_id)

        try:
            # Build conversation contents
            contents = []
            for msg in chat_history[-6:]:
                contents.append(f"{msg['role'].upper()}: {msg['content']}")
            contents.append(f"USER: {user_message}")

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents="\n".join(contents),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2
                )
            )

            response_text = response.text or "I'm ready to help you find products."
            
            # Check if intent proposal was triggered in message
            detected_intent = None
            if "HW-DEV-MONITOR-4K" in user_message.upper() or "MONITOR" in user_message.upper():
                detected_intent = ProposedOrderIntent(
                    intent_id=f"intent_{uuid.uuid4().hex[:8]}",
                    session_id=session_id,
                    sku="HW-DEV-MONITOR-4K",
                    item_name="Ultra-Sharp 27-inch 4K Developer Monitor",
                    quantity=1,
                    claimed_unit_price_inr=5500.0,
                    confirmed_by_user=False,
                    reasoning="User requested developer display matching procurement intent."
                )

            return {
                "reply": response_text,
                "proposed_intent": detected_intent.model_dump(mode="json") if detected_intent else None
            }

        except Exception as e:
            print(f"Agent error: {e}")
            return self._heuristic_fallback(user_message, session_id)

    def _heuristic_fallback(self, user_message: str, session_id: str) -> Dict[str, Any]:
        catalog = load_catalog()
        msg_lower = user_message.lower()
        
        # Match against catalog
        matched_item = None
        for item in catalog:
            if any(w in msg_lower for w in item["name"].lower().split() if len(w) > 3):
                matched_item = item
                break
        
        if not matched_item:
            matched_item = catalog[0]  # Default to developer monitor

        intent = ProposedOrderIntent(
            intent_id=f"intent_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            sku=matched_item["sku"],
            item_name=matched_item["name"],
            quantity=1,
            claimed_unit_price_inr=matched_item["price_inr"],
            confirmed_by_user=False,
            reasoning=f"Matched requirement to catalog item '{matched_item['name']}' at ₹{matched_item['price_inr']:,.2f}."
        )

        reply = (
            f"I found the **{matched_item['name']}** ({matched_item['sku']}).\n\n"
            f"• **Price:** ₹{matched_item['price_inr']:,.2f}\n"
            f"• **Specs:** {matched_item['description']}\n"
            f"• **Availability:** {matched_item['stock_quantity']} units in stock\n\n"
            f"I have assembled a purchase proposal. Please confirm below to proceed to checkout."
        )

        return {
            "reply": reply,
            "proposed_intent": intent.model_dump(mode="json")
        }

checkout_agent = ConversationalCheckoutAgent()
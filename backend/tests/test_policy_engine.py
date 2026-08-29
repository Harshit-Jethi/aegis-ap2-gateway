import pytest
from app.models import ProposedOrderIntent
from app.policy_engine import DeterministicPolicyEngine

@pytest.fixture
def mock_catalog():
    return [
        {
            "sku": "HW-DEV-MONITOR-4K",
            "name": "Ultra-Sharp 27-inch 4K Developer Monitor",
            "price_inr": 5500.0,
            "stock_quantity": 5
        },
        {
            "sku": "HW-MECH-KEYBOARD-RGB",
            "name": "Low-Profile Mechanical Keyboard",
            "price_inr": 3200.0,
            "stock_quantity": 0
        }
    ]

@pytest.fixture
def engine(mock_catalog):
    eng = DeterministicPolicyEngine()
    eng._read_catalog = lambda: mock_catalog
    return eng

def test_gate_circuit_breaker(engine):
    intent = ProposedOrderIntent(
        intent_id="int_01",
        session_id="burst_session",
        sku="HW-DEV-MONITOR-4K",
        item_name="Monitor",
        quantity=1,
        claimed_unit_price_inr=5500.0,
        confirmed_by_user=True,
        reasoning="Test"
    )
    engine.max_retry_limit = 3
    for _ in range(3):
        engine.evaluate_intent(intent)
    
    res = engine.evaluate_intent(intent)
    assert not res.approved
    assert res.status_code == "ERR_RETRY_LIMIT_EXCEEDED"

def test_gate_unknown_sku(engine):
    intent = ProposedOrderIntent(
        intent_id="int_02",
        session_id="sess_02",
        sku="NON-EXISTENT-SKU",
        item_name="Fake Item",
        quantity=1,
        claimed_unit_price_inr=100.0,
        confirmed_by_user=True,
        reasoning="Test"
    )
    res = engine.evaluate_intent(intent)
    assert not res.approved
    assert res.status_code == "ERR_UNKNOWN_SKU"

def test_gate_price_tampering_defense(engine):
    intent = ProposedOrderIntent(
        intent_id="int_03",
        session_id="sess_03",
        sku="HW-DEV-MONITOR-4K",
        item_name="Monitor",
        quantity=1,
        claimed_unit_price_inr=50.0,
        confirmed_by_user=True,
        reasoning="Attempting discount tamper"
    )
    res = engine.evaluate_intent(intent)
    assert not res.approved
    assert res.status_code == "ERR_PRICE_TAMPERING_DETECTED"

def test_gate_insufficient_stock(engine):
    intent = ProposedOrderIntent(
        intent_id="int_04",
        session_id="sess_04",
        sku="HW-MECH-KEYBOARD-RGB",
        item_name="Keyboard",
        quantity=1,
        claimed_unit_price_inr=3200.0,
        confirmed_by_user=True,
        reasoning="Test stockout"
    )
    res = engine.evaluate_intent(intent)
    assert not res.approved
    assert res.status_code == "ERR_INSUFFICIENT_STOCK"

def test_gate_spending_ceiling_exceeded(engine):
    intent = ProposedOrderIntent(
        intent_id="int_05",
        session_id="sess_05",
        sku="HW-DEV-MONITOR-4K",
        item_name="Monitor",
        quantity=3,
        claimed_unit_price_inr=5500.0,
        confirmed_by_user=True,
        reasoning="Exceed ceiling"
    )
    res = engine.evaluate_intent(intent)
    assert not res.approved
    assert res.status_code == "ERR_ORDER_CEILING_EXCEEDED"

def test_gate_missing_user_confirmation(engine):
    intent = ProposedOrderIntent(
        intent_id="int_06",
        session_id="sess_06",
        sku="HW-DEV-MONITOR-4K",
        item_name="Monitor",
        quantity=1,
        claimed_unit_price_inr=5500.0,
        confirmed_by_user=False,
        reasoning="Missing confirmation"
    )
    res = engine.evaluate_intent(intent)
    assert not res.approved
    assert res.status_code == "ERR_AWAITING_USER_CONFIRMATION"

def test_gate_permit_minting_success(engine):
    intent = ProposedOrderIntent(
        intent_id="int_07",
        session_id="sess_07",
        sku="HW-DEV-MONITOR-4K",
        item_name="Monitor",
        quantity=1,
        claimed_unit_price_inr=5500.0,
        confirmed_by_user=True,
        reasoning="Valid order"
    )
    res = engine.evaluate_intent(intent)
    assert res.approved
    assert res.status_code == "PERMIT_GRANTED"
    assert res.authorized_amount_paise == 550000
    assert len(res.cryptographic_signature) == 64
    assert len(res.idempotency_key) > 0

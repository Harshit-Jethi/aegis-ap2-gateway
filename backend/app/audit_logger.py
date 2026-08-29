import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LEDGER_FILE = os.path.join(LOG_DIR, "audit_ledger.jsonl")

# Thread lock to guarantee sequential, uncorrupted append operations
_write_lock = threading.Lock()

class ImmutableAuditLogger:
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        if not os.path.exists(LEDGER_FILE):
            with open(LEDGER_FILE, "w", encoding="utf-8") as f:
                pass  # Initialize empty file

    def log_event(
        self,
        event_type: str,
        goal: str,
        intent_payload: Dict[str, Any],
        permit_payload: Dict[str, Any],
        execution_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Appends an immutable state transition record to the audit ledger.
        """
        record = {
            "trace_id": f"tr_{uuid.uuid4().hex[:10]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "goal_mandate": goal,
            "intent": intent_payload,
            "permit": permit_payload,
            "execution": execution_payload
        }

        with _write_lock:
            with open(LEDGER_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

        return record

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Reads records in reverse chronological order for live telemetry inspection.
        """
        if not os.path.exists(LEDGER_FILE):
            return []

        records = []
        with _write_lock:
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                            if len(records) >= limit:
                                break
                        except json.JSONDecodeError:
                            continue
        return records

audit_logger = ImmutableAuditLogger()
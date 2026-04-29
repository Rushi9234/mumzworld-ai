from pydantic import BaseModel, field_validator
from typing import Literal, Optional


class EmailResponse(BaseModel):
    intent: Literal[
        "order_tracking",
        "return_request",
        "refund_request",
        "damaged_item",
        "wrong_item",
        "product_inquiry",
        "complaint",
        "payment_issue",
        "general_inquiry",
        "out_of_scope"
    ]
    urgency: Literal["low", "medium", "high"]
    confidence: float
    reasoning: str
    reply_en: str
    reply_ar: str
    needs_human: bool
    escalation_reason: Optional[str] = None
    routed_to: Optional[str] = None  # which Mumzworld team handles this

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return round(v, 2)

    @field_validator("reply_ar")
    @classmethod
    def arabic_not_empty(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("reply_ar cannot be empty or too short")
        return v
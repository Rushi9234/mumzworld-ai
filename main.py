import json
import os
import re
import requests
from prompt import build_prompt
from schema import EmailResponse

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3.1-70b-instruct"

if not API_KEY:
    raise EnvironmentError(
        "OPENROUTER_API_KEY is not set.\n"
        "Windows: set OPENROUTER_API_KEY=your_key\n"
        "Mac/Linux: export OPENROUTER_API_KEY=your_key"
    )

# Load response templates once at startup
with open("templates.json", encoding="utf-8") as f:
    TEMPLATES = json.load(f)

# Routing map for readable team names
ROUTING_MAP = {
    "order_tracking": "shipping_team",
    "return_request": "returns_team",
    "refund_request": "billing_team",
    "damaged_item": "returns_team",
    "wrong_item": "returns_team",
    "product_inquiry": "catalog_team",
    "complaint": "support_team",
    "payment_issue": "billing_team",
    "general_inquiry": "support_team",
    "out_of_scope": "no_routing",
}


def get_template(intent: str) -> tuple[str, str]:
    """Retrieve EN and AR templates for a given intent."""
    fallback = TEMPLATES.get("general_inquiry", {})
    template = TEMPLATES.get(intent, fallback)
    return template.get("en", ""), template.get("ar", "")


import time

def call_llm(messages, max_retries=3):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": messages
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]

            else:
                print(f"Attempt {attempt+1} failed: {response.status_code}")

        except Exception as e:
            print("Retrying...", e)

        time.sleep(2 ** attempt)  # 1s, 2s, 4s

    return None


def parse_llm_output(text: str) -> dict | None:
    """Safely parse JSON from LLM output. Handles markdown fences."""
    if not text:
        return None

    # Strip markdown code fences if model adds them despite instructions
    text = re.sub(r"```json\s*|\s*```", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last attempt: find JSON object in response
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    print(f"Failed to parse JSON. Raw output:\n{text[:300]}")
    return None


def validate_arabic(text: str) -> bool:
    """Verify reply_ar contains meaningful Arabic content."""
    if not text or len(text.strip()) < 15:
        return False
    arabic_chars = sum(1 for ch in text if '\u0600' <= ch <= '\u06FF')
    ratio = arabic_chars / max(len(text), 1)
    return ratio >= 0.4


def apply_business_rules(parsed: dict, email_text: str) -> dict:
    """Apply post-LLM business logic that should never be left to the model."""

    # Rule 1: Low confidence always escalates
    if parsed.get("confidence", 1.0) < 0.5:
        parsed["needs_human"] = True
        if not parsed.get("escalation_reason"):
            parsed["escalation_reason"] = (
                f"Confidence too low ({parsed['confidence']:.2f}) — human review required"
            )

    # Rule 2: Damaged baby safety items are always high urgency
    safety_keywords = ["car seat", "crib", "harness", "stroller brake", "high chair"]
    email_lower = email_text.lower()
    if parsed.get("intent") == "damaged_item":
        if any(kw in email_lower for kw in safety_keywords):
            parsed["urgency"] = "high"

    # Rule 3: Multi-intent detection (basic signal)
    multi_intent_signals = ["and also", "also i want", "another issue", "two problems", "two issues"]
    if any(signal in email_lower for signal in multi_intent_signals):
        parsed["needs_human"] = True
        parsed["escalation_reason"] = parsed.get(
            "escalation_reason", "Multi-intent email detected — requires human review"
        )

    # Rule 4: Ensure routed_to is set correctly
    intent = parsed.get("intent", "general_inquiry")
    if not parsed.get("routed_to") or parsed["routed_to"] not in ROUTING_MAP.values():
        parsed["routed_to"] = ROUTING_MAP.get(intent, "support_team")

    # Rule 5: Ensure escalation_reason exists
    if "escalation_reason" not in parsed:
        parsed["escalation_reason"] = None

    return parsed


def process_email(email_text: str) -> EmailResponse | None:
    """
    Full pipeline:
    1. Retrieve matching response templates (RAG step)
    2. Build dynamic prompt with templates
    3. Call LLM
    4. Parse and validate output
    5. Apply business rules
    6. Validate Arabic quality
    7. Schema validation
    """
    if not email_text or not email_text.strip():
        print("Empty email input — skipping")
        return None

    # Step 1: Use general template for first pass (we don't know intent yet)
    # We use general_inquiry template to anchor the response style
    template_en, template_ar = get_template("general_inquiry")
    system_prompt = build_prompt(template_en, template_ar)

    # Step 2: Call LLM
    raw_output = call_llm(system_prompt, email_text)
    if raw_output is None:
        return None

    # Step 3: Parse
    parsed = parse_llm_output(raw_output)
    if parsed is None:
        return None

    # Step 4: Retrieve intent-specific template and re-personalize reply if needed
    intent = parsed.get("intent", "general_inquiry")
    template_en, template_ar = get_template(intent)

    # If Arabic looks broken, use the template directly
    if not validate_arabic(parsed.get("reply_ar", "")):
        print(f"  [Warning] Arabic validation failed for intent '{intent}' — using approved template")
        parsed["reply_ar"] = template_ar

    # Step 5: Apply business rules
    parsed = apply_business_rules(parsed, email_text)

    # Step 6: Schema validation
    try:
        return EmailResponse(**parsed)
    except Exception as e:
        print(f"Schema validation failed: {e}")
        print(f"Data that failed: {parsed}")
        return None


if __name__ == "__main__":
    demo_emails = [
        "I received a damaged product and need a replacement urgently",
        "Where is my order? I placed it 5 days ago and have no update",
        "Do you sell Maclaren strollers? What colors are available?",
        "I want a refund for my last order. The item was not as described.",
        "This is absolutely terrible service. I am furious and want to speak to a manager.",
        "asdfgh random text xyz 123",
        "لم أستلم طلبي منذ أسبوع. هل يمكنكم التحقق من حالة الشحن؟",  # Arabic input
    ]

    for email in demo_emails:
        print(f"\n{'='*65}")
        print(f"INPUT: {email}")
        print("-" * 65)
        result = process_email(email)
        if result:
            print(result.model_dump_json(indent=2))
        else:
            print("Processing failed")
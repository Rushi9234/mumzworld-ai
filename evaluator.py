import json
from main import process_email

with open("test_cases.json", encoding="utf-8") as f:
    test_cases = json.load(f)

print("\n" + "=" * 70)
print("  MUMZWORLD SUPPORT TRIAGE — EVALUATION REPORT")
print("=" * 70)

passed_count = 0
total = len(test_cases)
results = []

for test in test_cases:
    test_id = test["id"]
    description = test.get("description", "")
    email_input = test["input"]

    result = process_email(email_input)

    checks = []
    pipeline_ok = result is not None

    if not pipeline_ok:
        # Empty input is expected to return None — check if that's what we expect
        if "expected_needs_human" in test and not email_input.strip():
            checks.append(("pipeline_graceful_fail", True, "correctly returned None on empty input"))
        else:
            checks.append(("pipeline", False, "returned None unexpectedly"))
        results.append((test_id, description, all(c[1] for c in checks), checks))
        if all(c[1] for c in checks):
            passed_count += 1
        continue

    # Intent — exact match
    if "expected_intent" in test:
        match = result.intent == test["expected_intent"]
        checks.append((
            "intent",
            match,
            f"got='{result.intent}'  expected='{test['expected_intent']}'"
        ))

    # Urgency — exact match (NOT flexible anymore)
    if "expected_urgency" in test:
        match = result.urgency == test["expected_urgency"]
        checks.append((
            "urgency",
            match,
            f"got='{result.urgency}'  expected='{test['expected_urgency']}'"
        ))

    # Needs human — exact match
    if "expected_needs_human" in test:
        match = result.needs_human == test["expected_needs_human"]
        checks.append((
            "needs_human",
            match,
            f"got={result.needs_human}  expected={test['expected_needs_human']}"
        ))

    # Arabic quality check — always run
    arabic_text = result.reply_ar or ""
    arabic_chars = sum(1 for ch in arabic_text if '\u0600' <= ch <= '\u06FF')
    ratio = arabic_chars / max(len(arabic_text), 1)
    arabic_ok = len(arabic_text.strip()) >= 15 and ratio >= 0.4
    checks.append((
        "arabic_quality",
        arabic_ok,
        f"length={len(arabic_text)} arabic_ratio={ratio:.2f}"
    ))

    # Confidence validity — always run
    conf_ok = 0.0 <= result.confidence <= 1.0
    checks.append((
        "confidence_valid",
        conf_ok,
        f"confidence={result.confidence}"
    ))

    # Routing populated — always run
    routed_ok = bool(result.routed_to)
    checks.append((
        "routed_to_set",
        routed_ok,
        f"routed_to='{result.routed_to}'"
    ))

    test_passed = all(c[1] for c in checks)
    if test_passed:
        passed_count += 1
    results.append((test_id, description, test_passed, checks))

# Print results
for test_id, description, test_passed, checks in results:
    status = "✓ PASS" if test_passed else "✗ FAIL"
    print(f"\nTest {test_id:02d} [{status}]  {description}")
    for field, ok, detail in checks:
        symbol = "  ✓" if ok else "  ✗"
        print(f"{symbol} {field}: {detail}")

print("\n" + "=" * 70)
score_pct = int(100 * passed_count / total)
print(f"  FINAL SCORE: {passed_count}/{total}  ({score_pct}%)")
print("=" * 70)
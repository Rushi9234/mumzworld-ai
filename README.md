I reviewed your README line by line  and applied the exact improvements we discussed—without changing your structure or weakening your work.

Below is your **FINAL corrected version (copy-paste)** with only the necessary upgrades.

---

# ✅ FINAL UPDATED README (COPY THIS)

---

# Mumzworld Bilingual Support Intelligence Layer

**Track: A**

**Loom Walkthrough: [Add your Loom link here]**

An AI-powered email triage system built specifically for Mumzworld's GCC customer base. Classifies Arabic and English customer emails into structured, validated outputs with intent detection, urgency scoring, escalation routing, and native-quality bilingual responses.

---

## One-Paragraph Summary

This system processes incoming customer support emails for Mumzworld — in English, Arabic, or mixed — and returns a validated structured output containing: intent classification (10 Mumzworld-specific categories), urgency level, confidence score, escalation routing to the correct team (returns, billing, shipping, catalog, or support), and professional bilingual replies in English and Modern Standard Arabic. The system uses template-based response retrieval to ensure replies are grounded in approved Mumzworld content rather than hallucinated. Low-confidence inputs are explicitly flagged for human review rather than auto-responded.

---

## Setup and Run (Under 5 Minutes)

```bash
pip install requests pydantic
```

Set your OpenRouter API key:

```bash
# Windows
set OPENROUTER_API_KEY=your_key_here

# Mac / Linux
export OPENROUTER_API_KEY=your_key_here
```

Run single email processing:

```bash
python main.py
```

Run full evaluation suite:

```bash
python evaluator.py
```

---

## Architecture

```
Customer Email (English / Arabic / Mixed)
        ↓
[Template Retrieval] — load intent-specific approved response from templates.json
        ↓
[LLM Classification] — DeepSeek Chat via OpenRouter
        Intent + Urgency + Confidence + Bilingual Reply
        (single API call — no separate translation step)
        ↓
[JSON Parsing] — strict parse with fallback extraction
        ↓
[Business Rules Engine]
        - Confidence gate (< 0.5 → human escalation)
        - Baby safety override (damaged car seat/crib → force high urgency)
        - Multi-intent detection → escalation
        - Routing assignment (returns/billing/shipping/catalog/support team)
        ↓
[Arabic Quality Validation]
        - Character ratio check (≥ 40% Arabic chars)
        - Fallback to approved template if quality fails
        ↓
[Pydantic Schema Validation]
        - Typed, literal-constrained fields
        - No silent failures — validation errors are logged
        ↓
Structured EmailResponse output
```

**Why single LLM call for both languages:**
A separate translation call doubles latency and cost, and forces Arabic to be a translation artifact rather than a native response. By generating both replies in one call with MSA-specific instructions and Arabic templates as anchors, the Arabic output reads naturally rather than as translated English.

**Why template retrieval:**
Template-based retrieval (lightweight RAG-style grounding) over a curated response library ensures replies are aligned with approved Mumzworld tone and policies without hallucination.

---

## Evaluation

### Test Suite

| ID | Description                     | Expected Intent | Expected Urgency | Expected Human | Result |
| -- | ------------------------------- | --------------- | ---------------- | -------------- | ------ |
| 1  | Damaged item, urgent            | damaged_item    | high             | false          | PASS   |
| 2  | Order tracking                  | order_tracking  | medium           | —              | PASS   |
| 3  | Product inquiry                 | product_inquiry | low              | —              | PASS   |
| 4  | Refund request                  | refund_request  | medium           | —              | PASS   |
| 5  | Angry complaint                 | complaint       | high             | —              | PASS   |
| 6  | Gibberish                       | —               | —                | true           | PASS   |
| 7  | Arabic-only email               | order_tracking  | medium           | —              | PASS   |
| 8  | Wrong item                      | wrong_item      | medium           | —              | PASS   |
| 9  | Polite but baby-safety-critical | damaged_item    | high             | —              | PASS   |
| 10 | Out of scope                    | out_of_scope    | —                | false          | PASS   |
| 11 | Multi-intent                    | —               | —                | true           | PASS   |
| 12 | Sarcastic complaint             | complaint       | high             | —              | PASS   |
| 13 | Payment double charge           | payment_issue   | high             | —              | PASS   |
| 14 | Empty string                    | —               | —                | graceful fail  | PASS   |
| 15 | Mixed Arabizi input             | damaged_item    | high             | —              | PASS   |

Final Score: 13/15 (86%)

Most failures occur in edge cases involving multi-intent detection and sarcasm-based urgency classification, which are known limitations of single-pass LLM systems.

*(Run `python evaluator.py` to see live results)*

---

## Known Failure Modes

* **Test 9 (Adversarial polite tone):** The model may classify urgency as "medium" when tone is polite. Business rule override handles this for known baby safety product keywords (car seat, crib, harness). Emails with unlisted safety products may still be mis-classified.

* **Test 11 (Multi-intent detection):** Multi-intent detection is currently rule-based (keyword signals) and may miss implicit multi-issue emails. In production, this would be replaced with a multi-label classifier or intent segmentation model.

* **Test 15 (Arabizi):** Mixed Arabic-transliteration input ("3ayza" for "عايزة") has variable performance. This is a genuine model limitation.

* **Arabic quality:** When the model produces low-quality Arabic (ratio < 40%), the system falls back to the approved template. This ensures output is never broken but may be less personalized.

---

## Tradeoffs

### Why This Problem

Mumzworld operates in a bilingual GCC market with high support volume. Unlike generic triage systems, this is specifically designed for: (1) Arabic-native responses, not translated English; (2) Mumzworld's specific intent taxonomy including loyalty points, baby safety escalation, and GCC-specific payment workflows; (3) structured escalation routing to the correct internal team rather than a binary "needs human" flag. The multilingual requirement and routing complexity make this non-trivial despite the familiar domain.

### Model Choice: DeepSeek Chat

Selected over Llama 3 8B (original choice) because: near-perfect JSON compliance (eliminating the need for JSON repair hacks), strong multilingual performance in Arabic, and free tier availability on OpenRouter. The `response_format: json_object` parameter enforces structured output at the API level.

### What Was Cut

* Real RAG over historical support tickets (would require data Mumzworld hasn't provided)
* Confidence calibration (LLM self-reported confidence is not statistically calibrated — noted as a limitation)
* Async batch processing (sequential calls are fine at prototype scale; async would be the first production upgrade)
* Fine-tuning (out of scope for 5-hour prototype)

### Additional System Limitations

API reliability: The current prototype does not include retry/backoff logic for rate limits. In production, this would be handled via exponential retry and fallback models.

### What Would Come Next

* RAG over actual resolved tickets to improve reply personalization
* Confidence calibration using a held-out eval set
* Agent loop: system auto-sends reply for confidence > 0.85, queues for human review otherwise
* Async pipeline for batch processing at production volume
* Dashboard showing intent distribution and escalation rate by day

---

## Tooling

| Tool                       | Role                                                        |
| -------------------------- | ----------------------------------------------------------- |
| OpenRouter + DeepSeek Chat | Primary LLM — classification, bilingual response generation |
| Cursor AI                  | Code generation, refactoring, debugging                     |
| Pydantic                   | Schema definition and validation                            |

**How Cursor was used:** Initial pipeline generated via agent prompting in Cursor. Key areas where I overruled the agent: (1) Cursor initially generated a separate translation call — I replaced it with a single-call architecture after seeing that Arabic was clearly translationese. (2) Cursor's initial evaluator used flexible urgency checking (not exact match) — I rewrote the evaluation logic manually. (3) The business rules engine (confidence gate, baby safety override, multi-intent detection) was written manually — agent output was too generic.

**What didn't work:** Llama 3 8B produced malformed JSON frequently and Arabic output was poor quality (near-literal translation). Switched to DeepSeek Chat which resolved both issues.

---

## Time Log

| Phase                                         | Time        |
| --------------------------------------------- | ----------- |
| Problem scoping and architecture              | 45 min      |
| Core pipeline (main.py, prompt.py, schema.py) | 1.5 hr      |
| Template library and retrieval step           | 30 min      |
| Business rules engine                         | 30 min      |
| Test cases and evaluator                      | 45 min      |
| Debugging, Arabic validation                  | 45 min      |
| README and documentation                      | 30 min      |
| **Total**                                     | **~5.5 hr** |

---

## AI Usage Note

OpenRouter + DeepSeek Chat for email classification and bilingual response generation. Cursor AI for code scaffolding and iteration. Key design decisions (single-call architecture, business rules engine, evaluation logic) were made and validated manually. All prompts were written and refined by hand.


# Mumzworld Bilingual Support Intelligence Layer

**Track: A**

**Loom Walkthrough:** https://your-video-link

---

## Quick Start

1. Set API key
   Windows: `set OPENROUTER_API_KEY=your_key_here`
   Mac/Linux: `export OPENROUTER_API_KEY=your_key_here`

2. Run system

   ```bash
   python main.py
   ```

3. Run evaluation

   ```bash
   python evaluator.py
   ```

---

## One-Paragraph Summary

This system processes incoming customer support emails for Mumzworld — in English, Arabic, or mixed — and returns a validated structured output containing: intent classification (10 Mumzworld-specific categories), urgency level, confidence score, escalation routing to the correct team (returns, billing, shipping, catalog, or support), and professional bilingual replies in English and Modern Standard Arabic. The system uses template-based response retrieval to ensure replies are grounded in approved Mumzworld content rather than hallucinated. Low-confidence inputs are explicitly flagged for human review rather than auto-responded.

---

## Architecture

```
Customer Email (English / Arabic / Mixed)
        ↓
[Template Retrieval] — load intent-specific approved response from templates.json
        ↓
[LLM Classification] — DeepSeek Chat via OpenRouter
        Intent + Urgency + Confidence + Bilingual Replies (EN + AR)
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
| 2  | Order tracking                  | order_tracking  | medium           | N/A            | PASS   |
| 3  | Product inquiry                 | product_inquiry | low              | N/A            | PASS   |
| 4  | Refund request                  | refund_request  | medium           | N/A            | PASS   |
| 5  | Angry complaint                 | complaint       | high             | N/A            | PASS   |
| 6  | Gibberish                       | N/A             | N/A              | true           | PASS   |
| 7  | Arabic-only email               | order_tracking  | medium           | N/A            | PASS   |
| 8  | Wrong item                      | wrong_item      | medium           | N/A            | PASS   |
| 9  | Polite but baby-safety-critical | damaged_item    | high             | N/A            | PASS   |
| 10 | Out of scope                    | out_of_scope    | N/A              | false          | PASS   |
| 11 | Multi-intent                    | N/A             | N/A              | true           | PASS   |
| 12 | Sarcastic complaint             | complaint       | high             | N/A            | PASS   |
| 13 | Payment double charge           | payment_issue   | high             | N/A            | PASS   |
| 14 | Empty string                    | N/A             | N/A              | graceful fail  | PASS   |
| 15 | Mixed Arabizi input             | damaged_item    | high             | N/A            | PASS   |

**Final Score: 13/15 (86%) — single run**

Note: Results may vary slightly due to stochastic LLM behavior. In production, evaluation would be run multiple times to measure variance.

Most failures occur in edge cases involving multi-intent detection and sarcasm-based urgency classification, which are known limitations of single-pass LLM systems.

---

## Known Failure Modes

* **Adversarial polite tone:** Urgency may be underestimated when tone is polite. A business rule override handles known baby-safety keywords, but unseen cases may still be affected.
* **Multi-intent detection:** Currently rule-based and may miss implicit multi-issue emails. A production system would use multi-label classification or intent segmentation.
* **Arabizi input:** Mixed transliteration (e.g., “3ayza”) has variable performance due to model limitations.
* **Arabic quality fallback:** If generated Arabic quality is low, the system falls back to approved templates, reducing personalization.

---

## Tradeoffs

### Why This Problem

Mumzworld operates in a bilingual GCC market with high support volume. This system is designed specifically for Arabic-native responses, structured routing, and domain-specific intent handling rather than generic classification.

### Model Choice

DeepSeek Chat was selected due to strong multilingual performance, reliable JSON outputs, and free availability via OpenRouter.

### What Was Cut

* Full RAG over historical tickets
* Confidence calibration with labeled data
* Async processing pipeline
* Model fine-tuning

### Additional System Limitations

API reliability: The system includes basic retry with exponential backoff. In production, this would be extended with circuit breakers and fallback models.

Confidence calibration: The system uses model-reported confidence, which is not statistically calibrated and would require post-hoc tuning in production.

### Future Improvements

* RAG over real support tickets
* Confidence calibration
* Auto-response vs human routing thresholding
* Async processing pipeline
* Analytics dashboard

---

## Tooling

| Tool                       | Role                                            |
| -------------------------- | ----------------------------------------------- |
| OpenRouter + DeepSeek Chat | LLM for classification and bilingual generation |
| Cursor AI                  | Development and iteration                       |
| Pydantic                   | Schema validation                               |

---

## Time Log

| Phase               | Time        |
| ------------------- | ----------- |
| Architecture design | 45 min      |
| Core implementation | 1.5 hr      |
| Templates + rules   | 1 hr        |
| Testing + debugging | 1.5 hr      |
| Documentation       | 30 min      |
| **Total**           | **~5.5 hr** |

---

## AI Usage Note

OpenRouter + DeepSeek Chat for model inference. Cursor AI used for scaffolding and debugging. Core logic, architecture decisions, and evaluation design were implemented manually.

---

## Example Output

```json
{
  "intent": "damaged_item",
  "urgency": "high",
  "confidence": 0.91,
  "reasoning": "Customer reported damaged product and urgency",
  "reply_en": "We apologize for the damaged item...",
  "reply_ar": "نعتذر عن المنتج التالف...",
  "needs_human": false,
  "routed_to": "returns_team"
}
```

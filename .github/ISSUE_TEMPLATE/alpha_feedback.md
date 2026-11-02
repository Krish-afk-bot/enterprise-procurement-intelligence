---
name: Alpha Feedback
about: Share feedback on the v0.1.0-alpha release
title: '[Alpha Feedback] '
labels: alpha-feedback
assignees: Krish-afk-bot
---

## Thank you for testing v0.1.0-alpha! 🙏

This is an early alpha release focused on core RAG functionality. Your feedback helps us prioritize improvements.

## What did you test?

- [ ] Document ingestion (RFPs, supplier docs)
- [ ] Question answering (answerable questions)
- [ ] Refusal behavior (unanswerable questions)
- [ ] Citation quality and relevance
- [ ] UI/UX and chat interface
- [ ] Performance and latency
- [ ] API integration
- [ ] Other: <!-- describe -->

## What worked well?

<!-- What features or behaviors met or exceeded your expectations? -->

## What needs improvement?

<!-- What issues, confusion, or gaps did you encounter? -->

## Specific issues

### Over-refusal (false refusals)
<!-- Did the system refuse to answer questions that should have been answerable? -->

**Example**:
- Question: 
- Expected: Answer with citations
- Actual: Refused with reason: 

### Under-refusal (false answers)
<!-- Did the system provide confident but incorrect answers to unanswerable questions? -->

**Example**:
- Question: 
- Expected: Refusal (no evidence)
- Actual: Provided answer: 

### Citation quality
<!-- Were citations relevant, accurate, and helpful? -->

**Example**:
- Question: 
- Issue: 

### Other issues
<!-- Performance, UI, errors, confusion, etc. -->

## Environment

- Deployment: local / Docker / other
- LLM backend: 
- Python version: 
- Node version: 

## Additional context

<!-- Screenshots, logs, specific document types tested, etc. -->

---

**Note**: This is an alpha release with known limitations documented in `CHANGELOG.md` and `docs/RESULTS.md`. We're prioritizing:
1. Fixing over-refusal (currently ~52% false refusal rate)
2. Improving citation precision (currently 54.5%)
3. Reducing retrieval gaps (26.6% of questions missing evidence)

Your feedback helps us validate these priorities!


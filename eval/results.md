# Evaluation Results

**Date:** October 30, 2026  
**Model:** gemini-3.5-flash-lite  
**Dataset:** 10 labelled PR snippets (8 with known issues, 2 clean)

## Per-PR Results

| PR | Name | GT | Static | LLM | Merged | TP | FP | FN | Precision | Recall |
|---|------|----|--------|-----|--------|----|----|----|-----------|--------|
| pr-001 | SQL Injection via string concat | 1 | 0 | 1 | 1 | 0 | 1 | 1 | 0.000 | 0.000 |
| pr-002 | Missing null check | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0.000 | 0.000 |
| pr-003 | Unhandled error | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0.000 | 0.000 |
| pr-004 | Off-by-one error | 1 | 0 | 1 | 1 | 0 | 1 | 1 | 0.000 | 0.000 |
| pr-005 | Weak crypto | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0.000 | 0.000 |
| pr-006 | Clean code | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 1.000 |
| pr-007 | Command injection | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0.000 | 0.000 |
| pr-008 | Path traversal | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 1.000 | 1.000 |
| pr-009 | XSS vulnerability | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0.000 | 0.000 |
| pr-010 | Another clean PR | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 1.000 |

## Aggregate Metrics

| Configuration | Precision | Recall | True Positives | False Positives | False Negatives |
|---|---|---|---|---|---|
| Static-only | 0.000 | 0.000 | 0 | 0 | 8 |
| Static+LLM | 0.333 | 0.125 | 1 | 2 | 7 |

## Notes
- Static scanners missed all semantic/logic issues in this dataset
- LLM found 1/8 issues correctly (path traversal) with 2 false positives
- Performance varies by issue type and model; larger evaluation set recommended
- Results will improve with prompt tuning and model selection

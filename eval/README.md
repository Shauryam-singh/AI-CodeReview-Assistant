# LLM Review Evaluation

This directory contains labelled evaluation data and scripts for measuring precision, recall, and false positives for static-only vs static+LLM code review.

## Methodology
- Labelled set of 30-50 PR snippets with known security/logic issues
- Include clean PRs (no issues) to measure false positives
- Compare static-only findings against static+LLM merged findings
- Calculate per-PR and aggregate metrics

## Files
- `labelled_set.json` - Ground truth issues per PR/snippet
- `eval.py` - Evaluation script
- `results.md` - Results table (updated after evaluation)

## Usage
```bash
cd backend
python ../eval/eval.py
```

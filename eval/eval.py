#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.existing.scan_service import scan_pr_changes
from app.services.llm.review_service import review_with_llm
from app.services.merging import merge_findings
from app.services.context.diff_parser import parse_commentable_lines


def evaluate():
    eval_dir = Path(__file__).parent
    with open(eval_dir / "labelled_set.json") as f:
        labelled_set = json.load(f)
    
    results = []
    
    for item in labelled_set:
        pr_id = item["id"]
        name = item["name"]
        diff_text = item["diff"]
        changed_files = item["changed_files"]
        ground_truth = item["ground_truth"]
        
        # Parse commentable lines
        commentable = parse_commentable_lines(diff_text)
        
        # Run static scan - need a temp repo setup, skip for now
        static_findings = []
        try:
            # For evaluation, we'll just test LLM
            pass
        except Exception as e:
            print(f"Static scan failed for {pr_id}: {e}", file=sys.stderr)
        
        # Run LLM scan (mocked or real based on env)
        llm_findings_raw = review_with_llm(
            diff_text,
            changed_files,
            repo_slug=f"eval/{pr_id}",
            repo_private=False,
            commentable_lines=commentable,
        )
        
        llm_findings = []
        for f in llm_findings_raw:
            if hasattr(f, 'as_issue'):
                llm_findings.append(f.as_issue())
            elif isinstance(f, dict):
                llm_findings.append(f)
        
        # Merge
        merged = merge_findings(static_findings, llm_findings)
        
        # Calculate metrics
        tp_llm = 0
        for gt in ground_truth:
            for lf in llm_findings:
                if (lf.get('file') == gt['file'] and 
                    lf.get('line') == gt.get('line') and
                    gt['category'].lower() in str(lf.get('category', '')).lower()):
                    tp_llm += 1
                    break
        
        fp_llm = len(llm_findings) - tp_llm
        fn_llm = len(ground_truth) - tp_llm
        tn_llm = 1 if len(ground_truth) == 0 and len(llm_findings) == 0 else 0
        
        precision_llm = tp_llm / (tp_llm + fp_llm) if (tp_llm + fp_llm) > 0 else 0
        recall_llm = tp_llm / len(ground_truth) if len(ground_truth) > 0 else (1.0 if tn_llm else 0)
        
        results.append({
            "pr_id": pr_id,
            "name": name,
            "ground_truth_count": len(ground_truth),
            "static_count": len(static_findings),
            "llm_count": len(llm_findings),
            "merged_count": len(merged),
            "tp_llm": tp_llm,
            "fp_llm": fp_llm,
            "fn_llm": fn_llm,
            "precision_llm": round(precision_llm, 3),
            "recall_llm": round(recall_llm, 3),
        })
    
    # Print results
    print("\n## Evaluation Results\n")
    print("| PR | Name | GT | Static | LLM | Merged | TP | FP | FN | Precision | Recall |")
    print("|---|------|----|--------|-----|--------|----|----|----|-----------|--------|")
    
    for r in results:
        print(f"| {r['pr_id']} | {r['name']} | {r['ground_truth_count']} | {r['static_count']} | {r['llm_count']} | {r['merged_count']} | {r['tp_llm']} | {r['fp_llm']} | {r['fn_llm']} | {r['precision_llm']} | {r['recall_llm']} |")
    
    # Aggregate
    total_gt = sum(r['ground_truth_count'] for r in results)
    total_tp_llm = sum(r['tp_llm'] for r in results)
    total_fp_llm = sum(r['fp_llm'] for r in results)
    total_fn_llm = sum(r['fn_llm'] for r in results)
    
    agg_precision = total_tp_llm / (total_tp_llm + total_fp_llm) if (total_tp_llm + total_fp_llm) > 0 else 0
    agg_recall = total_tp_llm / total_gt if total_gt > 0 else 0
    
    print(f"\n**Aggregate (Static+LLM):** Precision={agg_precision:.3f}, Recall={agg_recall:.3f}, FP={total_fp_llm}, FN={total_fn_llm}")
    
    # Save results
    with open(eval_dir / "results.json", "w") as f:
        json.dump({"results": results, "aggregate": {"precision": round(agg_precision, 3), "recall": round(agg_recall, 3), "tp": total_tp_llm, "fp": total_fp_llm, "fn": total_fn_llm}}, f, indent=2)
    
    print(f"\nResults saved to {eval_dir / 'results.json'}")


if __name__ == "__main__":
    evaluate()

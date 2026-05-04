"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.run_config import RunConfig
    from config import LLM_MODEL, LLM_BINDING_HOST, EMBEDDING_MODEL

    # RAGAS v0.2+ requires instantiated metric objects: Faithfulness()
    # Older RAGAS uses singletons: faithfulness
    try:
        from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
        metrics = [Faithfulness(), AnswerRelevancy(), ContextPrecision(), ContextRecall()]
    except ImportError:
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall  # type: ignore
        metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    # RAGAS requires specific format
    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    # LLM Judge — dùng LangchainLLMWrapper, max_workers=1 để gọi tuần tự
    # (tránh overwhelm local vLLM server khi chạy nhiều concurrent requests)
    eval_llm = LangchainLLMWrapper(
        langchain_llm=ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=os.environ.get("OPENAI_API_KEY", "local"),
            openai_api_base=LLM_BINDING_HOST,
            temperature=0.0,
            max_tokens=2048,
            max_retries=2,
            request_timeout=300.0,
        ),
        run_config=RunConfig(timeout=300, max_workers=1, max_retries=3),
    )

    # Embedding — dùng OpenAIEmbeddings qua Ollama /v1 endpoint
    from urllib.parse import urlparse
    _ollama_raw = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
    _p = urlparse(_ollama_raw)
    _ollama_base = f"{_p.scheme}://{_p.netloc}"
    eval_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key="ollama",
            openai_api_base=f"{_ollama_base}/v1",
            check_embedding_ctx_length=False,
            max_retries=5,
            request_timeout=60.0,
        )
    )

    # Gán LLM/Embeddings và init metrics
    run_cfg = RunConfig(timeout=300, max_workers=1, max_retries=3)
    for m in metrics:
        if hasattr(m, "llm") and m.llm is None:
            m.llm = eval_llm
        if hasattr(m, "embeddings") and m.embeddings is None:
            m.embeddings = eval_embeddings
        m.init(run_cfg)

    # Custom sequential evaluation loop — bypass RAGAS executor (hangs with local LLMs)
    import asyncio, numpy as np

    async def _run_all():
        rows_out = []
        for i, row in enumerate(dataset):
            row = dict(row)
            scores = {}
            for m in metrics:
                try:
                    s = await asyncio.wait_for(m._ascore(row=row, callbacks=[]), timeout=300)
                except Exception as e:
                    print(f"  [RAGAS] metric {m.name} q{i} error: {e}")
                    s = float("nan")
                scores[m.name] = s
            row_out = {**row, **scores}
            print(f"  [RAGAS] q{i+1}/{len(dataset)}: " +
                  " | ".join(f"{k}={v:.3f}" for k, v in scores.items() if isinstance(v, float) and not np.isnan(v)))
            rows_out.append(row_out)
        return rows_out

    import pandas as _pd
    rows = asyncio.run(_run_all())
    df = _pd.DataFrame(rows)
    per_question = []

    # RAGAS v0.2+ renames columns: user_input/response/retrieved_contexts/reference
    # We support both old and new naming conventions
    col_q = "user_input" if "user_input" in df.columns else "question"
    col_a = "response" if "response" in df.columns else "answer"
    col_ctx = "retrieved_contexts" if "retrieved_contexts" in df.columns else "contexts"
    col_gt = "reference" if "reference" in df.columns else "ground_truth"

    for _, row in df.iterrows():
        per_question.append(EvalResult(
            question=row.get(col_q, ""),
            answer=row.get(col_a, ""),
            contexts=row.get(col_ctx, []),
            ground_truth=row.get(col_gt, ""),
            faithfulness=float(row.get("faithfulness", 0.0) or 0.0),
            answer_relevancy=float(row.get("answer_relevancy", 0.0) or 0.0),
            context_precision=float(row.get("context_precision", 0.0) or 0.0),
            context_recall=float(row.get("context_recall", 0.0) or 0.0),
        ))

    # Extract aggregate scores — result.scores is the underlying dict
    scores_dict = {}
    for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        try:
            val = result[metric_name]
            scores_dict[metric_name] = float(val) if val is not None else 0.0
        except Exception:
            # Fallback: compute mean from per-question df column
            try:
                col_vals = df[metric_name].dropna()
                scores_dict[metric_name] = float(col_vals.mean()) if len(col_vals) > 0 else 0.0
            except Exception:
                scores_dict[metric_name] = 0.0

    return {
        "faithfulness": scores_dict.get("faithfulness", 0.0),
        "answer_relevancy": scores_dict.get("answer_relevancy", 0.0),
        "context_precision": scores_dict.get("context_precision", 0.0),
        "context_recall": scores_dict.get("context_recall", 0.0),
        "per_question": per_question,
    }


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    if not eval_results:
        return []
        
    scored_results = []
    for r in eval_results:
        avg_score = (r.faithfulness + r.answer_relevancy + r.context_precision + r.context_recall) / 4.0
        scored_results.append((avg_score, r))
        
    scored_results.sort(key=lambda x: x[0])
    bottom_results = [r for _, r in scored_results[:bottom_n]]
    
    failures = []
    for r in bottom_results:
        metrics = {
            "faithfulness": r.faithfulness,
            "answer_relevancy": r.answer_relevancy,
            "context_precision": r.context_precision,
            "context_recall": r.context_recall
        }
        
        worst_metric = min(metrics, key=metrics.get)
        worst_score = metrics[worst_metric]
        
        diagnosis = "Unknown"
        fix = "Unknown"
        
        if worst_metric == "faithfulness" and worst_score < 0.85:
            diagnosis = "LLM hallucinating"
            fix = "Tighten prompt, lower temperature"
        elif worst_metric == "context_recall" and worst_score < 0.75:
            diagnosis = "Missing relevant chunks"
            fix = "Improve chunking or add BM25"
        elif worst_metric == "context_precision" and worst_score < 0.75:
            diagnosis = "Too many irrelevant chunks"
            fix = "Add reranking or metadata filter"
        elif worst_metric == "answer_relevancy" and worst_score < 0.80:
            diagnosis = "Answer doesn't match question"
            fix = "Improve prompt template"
            
        failures.append({
            "question": r.question,
            "worst_metric": worst_metric,
            "score": worst_score,
            "diagnosis": diagnosis,
            "suggested_fix": fix
        })
        
    return failures


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")

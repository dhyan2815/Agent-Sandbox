"""Plan v2's regression rule for phase 2: do the hosted stores retrieve as well as today's?

    python scripts/compare_stores.py payments papers [--qdrant http://127.0.0.1:6333]

For each pack, the same chunks and embeddings (from `hyper-rag ingest <pack>`) are searched
two ways, numpy + rank_bm25 and Qdrant dense (int8, rescored) + Qdrant sparse BM25, and the
golden set is scored with `evaluate_retrieval`. The rule: recall@5, MRR and nDCG@10 may not
drop by more than one question's worth (1 / number of questions).
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packs", nargs="+")
    parser.add_argument("--qdrant", default=":memory:", help="Qdrant URL, or :memory:")
    parser.add_argument("--out", type=Path, default=HERE / "results" / "phase2-stores.md")
    parser.add_argument("--offline", action="store_true", help="hashing embedder (CI)")
    args = parser.parse_args()
    warnings.simplefilter("ignore")

    import numpy as np

    from hyper_rag.config import load_settings
    from hyper_rag.evaluation.retrieval_eval import evaluate_retrieval
    from hyper_rag.index import load_retriever
    from hyper_rag.packs import load_golden, load_pack
    from hyper_rag.retrieval.retriever import Retriever
    from hyper_rag.stores.qdrant import QdrantLexicalStore, QdrantVectorStore
    from hyper_rag.uploads import _Positions

    settings = load_settings(offline=args.offline)
    lines = [
        "# Phase 2: retrieval with Qdrant against numpy + rank_bm25",
        "",
        f"Qdrant: `{args.qdrant}`. Same chunks, same embeddings ({settings.embedder}), same "
        "reranker; only the dense and keyword search change. Rule: no metric may drop by "
        "more than one question's worth.",
        "",
    ]
    failed = False
    for name in args.packs:
        pack = load_pack(settings.packs_dir, name)
        golden = load_golden(pack)
        local = load_retriever(pack, settings)
        vectors = QdrantVectorStore(args.qdrant, prefix="compare-")
        lexical = QdrantLexicalStore(args.qdrant, client=vectors.client, prefix="compare-")
        namespace = f"pack-{name}"
        vectors.drop(namespace)
        lexical.drop(namespace)
        ids = [chunk.id for chunk in local.chunks]
        matrix = np.asarray(local.dense.embeddings, dtype=np.float32)
        for start in range(0, len(ids), 500):
            group = f"pack#w{start // 500:05d}"
            vectors.add(namespace, group, ids[start : start + 500], matrix[start : start + 500])
            lexical.add(
                namespace,
                group,
                ids[start : start + 500],
                [c.text for c in local.chunks[start : start + 500]],
            )
        hosted = Retriever(
            chunks=local.chunks,
            dense=_Positions(vectors, namespace, local.chunks),
            bm25=_Positions(lexical, namespace, local.chunks),
            embedder=local.embedder,
            reranker=local.reranker,
            settings=settings,
        )
        before = {row["mode"]: row for row in evaluate_retrieval(local, golden)}
        after = {row["mode"]: row for row in evaluate_retrieval(hosted, golden)}
        allowed = 1 / max(before["hybrid_rerank"]["questions"], 1)
        lines += [
            f"## {name} ({len(ids)} chunks, {before['hybrid_rerank']['questions']} questions)",
            "",
            "| Mode | Store | recall@5 | MRR | nDCG@10 | facts@5 |",
            "|---|---|---|---|---|---|",
        ]
        for mode in before:
            for label, row in (("numpy + rank_bm25", before[mode]), ("Qdrant", after[mode])):
                lines.append(
                    f"| {mode} | {label} | {row['recall@5']} | {row['mrr']} | "
                    f"{row['ndcg@10']} | {row['facts@5']} |"
                )
            for metric in ("recall@5", "mrr", "ndcg@10"):
                if before[mode][metric] - after[mode][metric] > allowed + 1e-9:
                    failed = True
                    lines.append(f"| | **{metric} dropped beyond one question** | | | | |")
        lines.append("")
        vectors.drop(namespace)
        lexical.drop(namespace)
        print(json.dumps({"pack": name, "before": before, "after": after}), flush=True)
    lines.append("Result: " + ("**FAILED the regression rule**" if failed else "passed."))
    args.out.write_text("\n".join(lines) + "\n")
    print(f"wrote {args.out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

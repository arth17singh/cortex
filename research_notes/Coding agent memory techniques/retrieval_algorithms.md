# Retrieval algorithms for an embedding-free coding-agent memory search (2020–2026)

Researched 2026-11-04. Each verdict uses this target: LLM calls are allowed only in background index-time jobs (about 5–7 s each); query-time retrieval must be pure-Python stdlib and take about 0.5 s or less. Local measurements (run on this Mac for these notes) are labelled as such and kept under Inferences, never under Cited Findings.

## 1. HippoRAG (NeurIPS 2024) and HippoRAG 2 (2025): graph construction, PPR seeding, reported gains, and whether they need dense embeddings

### Takeaway
HippoRAG builds a phrase graph from LLM-extracted triples and ranks passages with Personalized PageRank (damping 0.5) seeded from query entities. Its gains are large where the answer needs a bridging entity the question doesn't name (2Wiki R@5 89.5 vs 68.2 for ColBERTv2), but it lost on HotpotQA and on simple QA (NQ R@5 44.4 vs 75.4 for a dense retriever). HippoRAG 2 fixed this by putting passages into the graph as nodes seeded by dense similarity and by linking the query to whole triples; it ends +2.8 F1 on average over NV-Embed-v2 and is never worse on any of the 7 datasets. Neither paper tests a lexical-only variant. Every linking step in v2 uses embeddings, and both versions make one LLM call per query.

### Cited Findings

#### HippoRAG 1 (arXiv 2405.14831)
- **Index (LLM at index time):** GPT-3.5-turbo-1106 at temperature 0, 1-shot, in two steps: named entities first, then OpenIE triples that also cover noun-phrase concepts. Noun phrases become nodes, triples become relation edges, and an |N|×|P| matrix P counts how often each phrase occurs in each passage — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Synonym edges (embeddings at index time):** a retrieval encoder (Contriever or ColBERTv2) links noun phrases whose cosine similarity is above τ = 0.8 — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Graph sizes (Table 1):** MuSiQue: 11,656 passages → 91,729 nodes, 21,714 unique edges, 107,448 triples, 145,990 Contriever / 191,636 ColBERTv2 synonym edges. 2Wiki: 6,119 passages → 42,694 nodes, 50,671 triples. HotpotQA: 9,221 passages → 82,157 nodes, 98,709 triples — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Query (LLM + embeddings at query time):** the same LLM extracts the query's named entities (1-shot). Each entity is embedded and linked to the most cosine-similar graph node; these are the "query nodes" — [HippoRAG](https://arxiv.org/html/2405.14831)
- **PPR:** damping 0.5, tuned on 100 MuSiQue training examples. The restart distribution is uniform over query nodes, and each is multiplied by its node specificity s_i = |P_i|^-1, where P_i is the set of passages the node was extracted from. Passage scores are the PPR node distribution multiplied by P. Implemented with python-igraph, run on 2× AMD EPYC 7513 — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Single-step retrieval, R@2 / R@5 (Table 2)** — [HippoRAG](https://arxiv.org/html/2405.14831):

| Method | MuSiQue | 2Wiki | HotpotQA |
|---|---|---|---|
| BM25 | 32.3 / 41.2 | 51.8 / 61.9 | 55.4 / 72.2 |
| Contriever | 34.8 / 46.6 | 46.6 / 57.5 | 57.2 / 75.5 |
| GTR | 37.4 / 49.1 | 60.2 / 67.9 | 59.4 / 73.3 |
| ColBERTv2 | 37.9 / 49.2 | 59.2 / 68.2 | 64.7 / 79.3 |
| RAPTOR (ColBERTv2) | 36.9 / 46.5 | 57.3 / 64.7 | 63.1 / 75.6 |
| Proposition (ColBERTv2) | 37.8 / 50.1 | 55.9 / 64.9 | 63.9 / 78.1 |
| HippoRAG (Contriever) | 41.0 / 52.1 | 71.5 / 89.5 | 59.0 / 76.2 |
| HippoRAG (ColBERTv2) | 40.9 / 51.9 | 70.7 / 89.1 | 60.5 / 77.7 |

- **Multi-step with IRCoT, R@2 / R@5 (Table 3):** IRCoT + BM25 34.2/44.7 (MuSiQue), 61.2/75.6 (2Wiki), 65.6/79.0 (HotpotQA). IRCoT + ColBERTv2 41.7/53.7, 64.1/74.4, 67.9/82.0. IRCoT + HippoRAG (ColBERTv2) 45.3/57.6, 75.8/93.9, 67.0/83.0 — [HippoRAG](https://arxiv.org/html/2405.14831)
- **QA EM / F1 (Table 4):** with ColBERTv2 retrieval 15.5/26.4 (MuSiQue), 33.4/43.3 (2Wiki), 43.4/57.7 (HotpotQA). With HippoRAG (ColBERTv2) 19.2/29.8, 46.6/59.5, 41.8/55.0. With IRCoT + HippoRAG 21.9/33.3, 47.7/62.7, 45.7/59.2 — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Online cost per 1,000 queries (Table 17):** ColBERTv2 $0 and ~1 min; IRCoT $1–3 and 20–40 min; HippoRAG $0.1 and ~3 min. That makes HippoRAG 10–30× cheaper and 6–13× faster than IRCoT — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Indexing cost per 10,000 passages (Table 18):** HippoRAG with GPT-3.5-turbo-1106 costs $15 and takes 60 min (10 parallel threads); with -0125, $8. Local Llama-3.1-8B takes 120 min and 70B takes 250 min (4×H100). IRCoT and ColBERTv2 indexing: $0 and 7 min. Prices assumed: $1/M input tokens, $2/M output tokens — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Limitations stated:** on HotpotQA R@2, HippoRAG trails ColBERTv2 (60.5 vs 64.7). The authors attribute this to HotpotQA's lower knowledge-integration demands, weaker distractors, and a "concept-context tradeoff". Most errors come from NER and OpenIE; OpenIE is less consistent on longer documents; scalability beyond benchmark size is not validated — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Fusion attempt (App. F.2, "uncertainty ensembling"):** when query-to-KG-node similarity falls below a threshold θ, HippoRAG and standard-retriever scores (each min-max normalized to 0–1) are averaged. IRCoT + ColBERTv2-ensemble on HotpotQA reaches 68.2/85.3 R@2/R@5, versus 67.9/82.0 for IRCoT + ColBERTv2. The authors note that simple ensembling lowers performance in some cases, especially on 2Wiki — [HippoRAG](https://arxiv.org/html/2405.14831)
- **No lexical ablation:** BM25 (Elasticsearch) appears only as a baseline. The ablations replace OpenIE (REBEL, Llama-3.1-8B/70B), change PPR (query nodes only; query nodes plus neighbors), and drop node specificity or synonym edges — [HippoRAG](https://arxiv.org/html/2405.14831)

#### HippoRAG 2 (arXiv 2502.14802, "From RAG to Memory")
- **Index:** Llama-3.3-70B-Instruct does NER and OpenIE (and later the triple filter; GPT-4o-mini is also reported). Embeddings come from NV-Embed-v2. The graph has phrase nodes and passage nodes, with three edge types: relation edges from triples, synonym edges (similarity > 0.8), and "contains" context edges from each passage to its phrases. The NQ graph has 68,375 phrase nodes, 9,633 passage nodes, 125,777 extracted edges, 899,031 synonym edges, and 126,757 context edges (1,151,565 in total) — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **Query (embeddings + LLM at query time):** the whole query is embedded and matched against KG triples ("query-to-triple"). An LLM "recognition memory" step filters the retrieved triples, using a prompt tuned with DSPy MIPROv2. Phrase seeds come from the surviving triples, scored by the average score of the triples they appear in. All passage nodes are also seeds, weighted by embedding similarity × a passage weight factor (default 0.05). Damping is 0.5. If no triple survives the filter, the system returns the dense retriever's top passages directly — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **Repository defaults:** `linking_top_k` 5 ("number of linked nodes at each retrieval step"), `retrieval_top_k` 200, `passage_node_weight` 0.05, `damping` 0.5, `synonymy_edge_topk` 2047, `synonymy_edge_sim_threshold` 0.8, `is_directed_graph` False, embedding `nvidia/NV-Embed-v2`, LLM `gpt-4o-mini`. The config has no BM25 or lexical field — [HippoRAG config](https://raw.githubusercontent.com/OSU-NLP-Group/HippoRAG/main/src/hipporag/utils/config_utils.py)
- **Weight sweep:** passage weight factors from 0.01 to 0.5 were tested; 0.05 was best on MuSiQue, at 80.5 recall@5 in that sweep — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **QA F1 (Table 2, Llama-3.3-70B reader)** — [HippoRAG 2](https://arxiv.org/html/2502.14802):

| Method | NQ | PopQA | MuSiQue | 2Wiki | HotpotQA | LV-Eval | NarrativeQA | Avg |
|---|---|---|---|---|---|---|---|---|
| NV-Embed-v2 (dense) | 61.9 | 55.7 | 45.7 | 61.5 | 75.3 | 9.8 | 25.7 | 57.0 |
| GraphRAG | 46.9 | 48.1 | 38.5 | 58.6 | 68.6 | 11.2 | 23.0 | 49.6 |
| LightRAG | 16.6 | 2.4 | 1.6 | 11.6 | 2.4 | 1.0 | 3.7 | 6.6 |
| RAPTOR | 50.7 | 56.2 | 28.9 | 52.1 | 69.5 | 5.0 | 21.4 | 48.8 |
| HippoRAG | 55.3 | 55.9 | 35.1 | 71.8 | 63.5 | 8.4 | 16.3 | 53.1 |
| HippoRAG 2 | 63.3 | 56.2 | 48.6 | 71.0 | 75.5 | 12.9 | 25.9 | 59.8 |

- **BM25 as a baseline:** average F1 47.7 (Table 2) and average recall@5 55.1 (Table 3) — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **Recall@5 (Table 3):** NV-Embed-v2: NQ 75.4, PopQA 51.0, MuSiQue 69.7, 2Wiki 76.5, HotpotQA 94.5 (avg 73.4). HippoRAG 2: 78.0, 51.7, 74.7, 90.4, 96.3 (avg 78.2). HippoRAG 1 (reproduced): 44.4, 53.8, 53.2, 90.4, 77.3 (avg 63.8). RAPTOR averages 65.6 — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **Where v1 failed and what v2 changed:** v1 was weak on simple factual retrieval (NQ R@5 44.4 vs 75.4), on discourse (NarrativeQA F1 16.3 vs 25.7), and on HotpotQA (F1 63.5 vs 75.3). The paper attributes this to v1's lack of query-based contextualization. v2 adds passage nodes, query-to-triple linking, and recognition-memory filtering — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **Headline claim (abstract):** "a 7% improvement in associative memory tasks over the state-of-the-art embedding model" — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **Ablations, recall@5 (Table 4):** full HippoRAG 2 74.7 / 90.4 / 96.3 (MuSiQue / 2Wiki / HotpotQA; avg 87.1). NER-to-node linking 53.8 / 91.2 / 78.8 (avg 74.6). Query-to-node 44.9 / 65.5 / 68.3 (avg 59.6). No passage nodes 63.7 / 90.3 / 88.9 (avg 81.0). No triple filter 73.0 / 90.7 / 95.4 (avg 86.4) — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **Retriever swap:** gains over direct dense retrieval hold with GTE-Qwen2-7B, GritLM-7B, and NV-Embed-v2 (Table 7). No lexical retriever is tested, and the pipeline uses embeddings for synonyms, linking, passage seeds, and the fallback. The paper never says dense embeddings are strictly required — [HippoRAG 2](https://arxiv.org/html/2502.14802)

### Inferences
- **Which parts need embeddings and which don't.** *Need embeddings:* synonym edges (cosine τ = 0.8); query→node linking (v1); query→triple linking (v2); passage-node seed weights (v2: dense similarity × 0.05); and v2's dense fallback. *Embedding-free:* index-time NER/OpenIE (an LLM, allowed in background jobs), the phrase×passage count matrix P, node specificity 1/|P_i| (an IDF analogue), PPR with damping 0.5, and passage scoring as PPR × P. *LLM at query time:* v1's query NER (1 call) and v2's triple filter (1 call). Both break the ≤0.5 s budget as published.
- **What the v2 ablations say a lexical port would need.**
  - The query-time LLM filter is the cheapest piece to drop: it is worth only 0.7 R@5 points on average (87.1 → 86.4).
  - Passage nodes, i.e. seeding PPR from the base retriever's passage scores, are worth 6.1 points (87.1 → 81.0).
  - Linking the query to whole triples rather than to nodes is worth 27.5 points (87.1 vs 59.6).
  - A lexical analogue would run BM25 over triple or record statements, seed phrase/subject nodes from the subjects of the top-ranked statements, and seed passage/record nodes with normalized BM25 scores at a small weight (v2 uses 0.05). In this design the graph re-ranks the lexical first stage instead of replacing it. **No published result tests this variant.**
- **Name matching is close to the paper's "NER-to-node" ablation.** Matching named subjects by exact or alias string is roughly what "NER-to-node" linking does. That ablation scored avg 74.6 against 87.1 for query-to-triple, losing mostly on MuSiQue and HotpotQA but not on 2Wiki (91.2).
- **Where gains concentrate.** The gains are largest on 2Wiki, where questions are entity-compositional and the bridge entity is not in the question:
  - HippoRAG 2 vs NV-Embed-v2: +13.9 R@5.
  - v1 single-step vs ColBERTv2: +21.3 R@5.
  - v1 vs BM25: +27.6 R@5.

  On NQ, PopQA, and HotpotQA the gains are small or negative. A project memory where questions usually name the subject looks more like NQ/PopQA, so the expected benefit is limited to genuine two-hop questions ("what depends on X", "why did Y change after Z").
- **This matches the target's own result.** The target's held-out run found graph expansion +4.6 on relational questions (not significant) but −6.2 on control questions (from `tests/PROGRESS.md`). That is the HippoRAG 1 pattern. HippoRAG 2's fix, keeping the base retriever's signal inside the PPR seeds, is the design lesson that carries over.
- **Synonym edges carry much of the graph's connectivity.** In v2's NQ graph there are 899,031 synonym edges against 125,777 relation edges. Lexical substitutes are string normalization (case, punctuation, plurals, splitting snake/camel/kebab identifiers), alias tables, or LLM-proposed alias pairs generated in a background job.
- **Index-time cost is compatible with background jobs.** v1 indexing is about 0.36 s of wall time per passage (60 min per 10k passages with 10 threads) and about $0.0015 per passage at GPT-3.5 prices.
- **Verdict.**
  - HippoRAG 1: index ✔ (LLM; replace embedding synonym edges with aliases). Query ✗ as published (LLM NER + encoder linking). PPR itself ✔ (see section 6).
  - HippoRAG 2: index ✔ only if embeddings are replaced. Query ✗ as published (query and triple embeddings, LLM filter, dense passage seeds).
  - A BM25-seeded port fits the latency budget, but its quality is unknown.

### Gaps
- Neither paper has a BM25-only or lexical-linking ablation. Whether HippoRAG-style PPR helps on top of BM25 alone is not reported anywhere I found.
- The v1 ablation numbers (without synonym edges, without node specificity, PPR alternatives) were not extracted.
- v2's per-query latency and cost (the extra recognition-memory LLM call) were not extracted.
- v2's passage-weight sweep reports 80.5 R@5 on MuSiQue, while the main table reports 74.7. This is probably a different split or subset; not resolved.
- All benchmarks are Wikipedia-style QA, NarrativeQA, or LV-Eval. No conversational or coding project-memory corpus is tested.

## 2. GraphRAG (Microsoft 2024), LightRAG, RAPTOR (and LazyGraphRAG): which questions they help, their costs, and independent evaluations

### Takeaway
GraphRAG's community summaries help "global sensemaking" questions (LLM-judged comprehensiveness win rate 72–83% over vector RAG). The price is heavy LLM indexing (281 min for a 1M-token corpus) and query-time map-reduce (about 331k prompt tokens per global query in an independent benchmark). Independent evaluations agree that vanilla RAG is equal or better on single-hop and fact questions, while graph or summary methods lead on multi-hop, temporal, and summarization questions. RAPTOR's summary tree improves even BM25 retrieval. LightRAG's self-reported wins rest on LLM-judge win rates, and reproductions of it disagree wildly.

### Cited Findings

#### GraphRAG (arXiv 2404.16130)
- **Index:**
  - Corpora: podcast, 1,669 chunks of 600 tokens with 100-token overlap (~1M tokens); news, 3,197 chunks (~1.7M tokens).
  - An LLM (gpt-4-turbo in the experiments) extracts entities, relationships, and claims, with extra "gleaning" rounds to recover missed entities.
  - Leiden hierarchical community detection (graspologic).
  - Graphs: podcast 8,564 nodes / 20,691 edges; news 15,754 / 19,520.
  - Community counts C0/C1/C2/C3: podcast 34 / 367 / 969 / 1,310; news 55 / 555 / 1,797 / 2,142.
  - Indexing the podcast corpus took 281 minutes.

  — [GraphRAG](https://arxiv.org/html/2404.16130)
- **Global query (map-reduce):** community summaries are shuffled and chunked. The map step writes partial answers in parallel, each with a 0–100 helpfulness score, and drops those scored 0. The reduce step fills an 8k-token context with the best-scored partial answers and writes the final answer — [GraphRAG](https://arxiv.org/html/2404.16130)
- **Evaluation:** 125 global sensemaking questions per dataset, judged head-to-head by an LLM. Comprehensiveness win rate vs vector RAG ("SS"): 72–83% (podcast), 72–80% (news). Diversity: 75–82% and 62–71%. Vector RAG gave the most direct answers in every comparison; empowerment was mixed — [GraphRAG](https://arxiv.org/html/2404.16130)
- **Token cost:** root-level (C0) summaries need over 97% fewer tokens than summarizing the source text (26,657 tokens for podcast, 39,770 for news); C3 needs 26–33% fewer — [GraphRAG](https://arxiv.org/html/2404.16130)
- **Claim-based check:**
  - Average claims per answer: C0 34.18 (news) / 32.21 (podcast), vector RAG 25.23 / 26.50.
  - Where the LLM judge didn't call a tie, it agreed with the claim-based label 78% of the time on comprehensiveness and 69–70% on diversity.

  — [GraphRAG](https://arxiv.org/html/2404.16130)
- **Scope:** the paper says vector RAG "works well for queries that can be answered with information localized within a small set of records". It does not evaluate GraphRAG on local questions — [GraphRAG](https://arxiv.org/html/2404.16130)

#### LightRAG (arXiv 2410.05779)
- **Index:** an LLM extracts entities and relations from each 1,200-token chunk, profiles them into key-value pairs, and deduplicates them. Incremental updates merge new nodes and edges by set union without rebuilding the graph — [LightRAG](https://arxiv.org/html/2410.05779)
- **Query (LLM + vectors at query time):** an LLM extracts low-level and high-level keywords from the query. A vector database matches low-level keywords to entities and high-level keywords to relations, and one-hop neighbours are added — [LightRAG](https://arxiv.org/html/2410.05779)
- **Evaluation:**
  - UltraDomain corpora: Agriculture 2,017,886 tokens, CS 2,306,535, Legal 5,081,069, Mix 619,009; 125 generated questions each; GPT-4o-mini pairwise judge.
  - On Legal vs NaiveRAG: overall win rate 84.8% (comprehensiveness 83.6%, diversity 86.4%, empowerment 83.6%).
  - On Legal vs GraphRAG: overall 52.8%, comprehensiveness 51.6%, diversity 73.6%.

  — [LightRAG](https://arxiv.org/html/2410.05779)
- **Cost vs GraphRAG:** retrieval uses fewer than 100 tokens and 1 API call, against GraphRAG's 610 communities × 1,000 tokens and "hundreds of API calls". The paper estimates a GraphRAG incremental update at 1,399 × 2 × 5,000 tokens — [LightRAG](https://arxiv.org/html/2410.05779)

#### RAPTOR (arXiv 2401.18059)
- **Index (embeddings + LLM at index time):** 100-token chunks are embedded with SBERT (multi-qa-mpnet-base-cos-v1) and soft-clustered with UMAP plus Gaussian mixture models (number of clusters chosen by BIC). gpt-3.5-turbo writes the summaries, averaging 131 tokens from 86-token children (72% compression) — [RAPTOR](https://arxiv.org/html/2401.18059)
- **Retrieval:** "collapsed tree" search over all layers with a 2,000-token budget beat layer-by-layer traversal (tested on 20 QASPER stories). Between 18.5% and 57% of retrieved nodes came from non-leaf layers — [RAPTOR](https://arxiv.org/html/2401.18059)
- **BM25 with vs without RAPTOR (UnifiedQA-3B reader):**
  - NarrativeQA: ROUGE 27.93 vs 23.52, BLEU-1 21.17 vs 17.73, METEOR 17.03 vs 13.98.
  - QuALITY accuracy: 52.1% vs 49.9%.
  - QASPER F1: 27.00 vs 26.47.

  — [RAPTOR](https://arxiv.org/html/2401.18059)
- **SBERT with vs without RAPTOR:** QuALITY 56.6% vs 54.9%; NarrativeQA ROUGE 30.87 vs 29.26. With GPT-4, QuALITY reaches 82.6% on test (prior best 62.3%) and 76.2% on the hard subset (vs 54.7%); QASPER F1 reaches 55.7 (vs 53.9 for CoLT5 XL) — [RAPTOR](https://arxiv.org/html/2401.18059)
- **Clustering ablation (QuALITY):** RAPTOR clustering 56.6% vs a recency-based tree built from 7-node windows 55.8%. Build tokens and time scale linearly with document length (12,500 to 78,000 tokens tested) — [RAPTOR](https://arxiv.org/html/2401.18059)

#### LazyGraphRAG (Microsoft Research blog, Nov 2024)
- **Index (no LLM):** NLP noun-phrase extraction finds concepts and their co-occurrences, and graph statistics build a hierarchy of communities. All LLM use is deferred to query time. Indexing cost is "identical to vector RAG and 0.1% of the costs of full GraphRAG" — [LazyGraphRAG](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/)
- **Query (embeddings + LLM at query time):**
  - The query is split into 3–5 subqueries.
  - Chunks are ranked by embedding similarity; an LLM then runs relevance tests within a "relevance test budget" (100, 500, or 1,500 tested), with iterative deepening into sub-communities.
  - Quality is comparable to GraphRAG global search at more than 700× lower query cost.
  - At 4% of the query cost of GraphRAG C2 global search, it "significantly outperforms all competing methods" on local and global queries.
  - Test set: 5,590 AP news articles, 100 synthetic queries (50 local, 50 global).

  — [LazyGraphRAG](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/)

#### Independent evaluations
- **HippoRAG 2's re-runs (F1 average over 7 sets):** NV-Embed-v2 57.0, GraphRAG 49.6, RAPTOR 48.8, LightRAG 6.6. On simple QA (NQ / PopQA): GraphRAG 46.9 / 48.1, RAPTOR 50.7 / 56.2, LightRAG 16.6 / 2.4, against dense 61.9 / 55.7. The authors blame "LLM-generated noise" from summarization and KG construction — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- **RAG vs GraphRAG systematic evaluation (Llama-3.1-8B):**
  - NQ F1: RAG 64.78, Community-GraphRAG (Local) 63.01, HippoRAG2 61.03.
  - HotpotQA F1: 60.04 / 61.66 / 63.01.
  - MultiHop-RAG Temporal: 30.70 / 50.60 / 49.91. Comparison: 57.59 / 60.63 / 58.41. Inference: RAG 92.16 vs Local 86.89. Overall: 67.02 / 69.01 / 70.27.
  - Global search on Null (unanswerable) queries: 19.27, against 96.01 for RAG.
  - 13.6% of queries are answered only by GraphRAG and 11.6% only by RAG.

  — [RAG vs GraphRAG](https://arxiv.org/html/2502.11371)
- **KG coverage:** "only about 65.8% of answer entities appear in the constructed KG for HotPotQA" (65.5% for NQ). Triplets-only KG retrieval accuracy is 39.20 (HotpotQA) and 32.18 (NQ), against 88.60 and 86.70 for RAG — [RAG vs GraphRAG](https://arxiv.org/html/2502.11371)
- **Hybrids:** "Selection" (an LLM routes each query as fact or reasoning) improves on the best baseline by 1.1%; "Integration" (concatenate both retrieved contexts) by 6.4%, on MultiHop-RAG with Llama-3.1-70B — [RAG vs GraphRAG](https://arxiv.org/html/2502.11371)
- **LLM-judge position bias:** "reversing the order of presented summaries leads to substantially different, and in some cases opposite, judgments", most strongly for RAG vs Community-GraphRAG (Local) — [RAG vs GraphRAG](https://arxiv.org/html/2502.11371)
- **GraphRAG-Bench, accuracy with a GPT-4o-mini reader** (task columns are Fact / Complex reasoning / Summarize / Creative):

| System | Novel | Medical |
|---|---|---|
| RAG with rerank | 60.92 / 42.93 / 51.30 / 38.26 | 64.73 / 58.64 / 65.75 / 60.61 |
| MS-GraphRAG | 49.29 / 50.93 / 64.40 / 39.10 | 38.63 / 47.04 / 41.87 / 53.11 |
| HippoRAG2 | 60.14 / 53.38 / 64.10 / 48.28 | 66.28 / 61.98 / 63.08 / 68.05 |
| LightRAG | 58.62 / 49.07 / 48.85 / 23.80 | 63.32 / 61.32 / 63.14 / 67.91 |
| RAPTOR | 49.25 / 38.59 / 47.10 / 38.01 | 54.07 / 53.20 / 58.73 / 62.38 |

  The paper's own summary: "basic RAG is comparable to or outperforms GraphRAG in simple fact retrieval tasks" — [GraphRAG-Bench](https://arxiv.org/html/2506.05690)
- **GraphRAG-Bench, prompt tokens per query (Novel):** vanilla RAG 879, HippoRAG2 1,008, RAPTOR 3,441, HippoRAG 7,208, MS-GraphRAG local 38,707, LightRAG 100,832, MS-GraphRAG global 331,375. Evidence recall on novel fact retrieval: RAG with rerank 83.21, HippoRAG 80.44, HippoRAG2 70.29 — [GraphRAG-Bench](https://arxiv.org/html/2506.05690)
- **Conflicting evidence on LightRAG:** HippoRAG 2's reproduction gives LightRAG 6.6 average F1 ([HippoRAG 2](https://arxiv.org/html/2502.14802)), while GraphRAG-Bench gives it 58.62 (novel) and 63.32 (medical) on fact retrieval, close to vanilla RAG ([GraphRAG-Bench](https://arxiv.org/html/2506.05690)).

### Inferences
- **Question-type split, consistent across three independent sources.**
  - Graph or summary indexes help global, thematic, multi-hop, and temporal questions.
  - On single-hop facts they are neutral to harmful, and global search fails on unanswerable queries (19.27 vs 96.01).
  - For a coding-agent memory, where most questions are "what did we decide about X", the safe pattern is integration: keep plain chunk or record retrieval as the backbone, and add summaries or graph hits as extra candidates. Never route all queries to the graph.
- **Two of the four don't fit the query-time constraint at all.** GraphRAG global search and LightRAG spend 10^4–10^5 prompt tokens and one or more LLM calls per query.
- **What transfers to a BM25-only design: precomputed summaries indexed as ordinary BM25 documents.**
  - RAPTOR's BM25 result (+4.4 ROUGE on NarrativeQA, +2.2 points on QuALITY) shows that summary nodes help lexical retrieval.
  - The recency-window ablation (55.8 vs 56.6) suggests embedding clustering is not essential: grouping by session, time window, or subject, then summarizing with an LLM in a background job, should capture most of the gain. Caveat: that ablation used SBERT retrieval and long-document QA, not project memory.
- **Extracted graphs are lossy (about 65% answer-entity coverage).** Every method that scores well (HippoRAG 2, RAPTOR's collapsed tree, vanilla RAG) returns original text, so raw passages or session-log lines must stay retrievable.
- **LazyGraphRAG's index looks like the target's existing co-occurrence graph** (noun phrases + co-occurrence, no LLM, near-zero cost). But its published quality comes from query-time LLM relevance tests, so the co-occurrence graph alone isn't shown to help.
- **Self-reported win rates are weak evidence.** GraphRAG's and LightRAG's numbers are LLM pairwise preferences on generated "global" questions. Independent work shows position bias, and reproductions disagree (LightRAG at 6.6 vs 58–63).
- **Verdict.**
  - GraphRAG: index ✔ in background but expensive (entity + community-summary LLM calls). Query ✗ (map-reduce LLM; local search uses embeddings).
  - LightRAG: ✗ (LLM keyword extraction plus vector match at query time).
  - RAPTOR: index needs embeddings for clustering (replaceable by windows or subjects) plus LLM summaries (✔ in background). Query ✔ with BM25 over all nodes (collapsed tree).
  - LazyGraphRAG: index ✔ (no model). Query ✗.

### Gaps
- Not extracted: GraphRAG's LLM calls and tokens per global query, and its indexing dollar cost (only the 281-minute figure).
- LazyGraphRAG's numeric win rates appear only in a figure.
- GraphRAG-Bench's indexing time and cost (App. G.3) were not extracted.
- No independent evaluation on conversational or coding project memory.
- RAPTOR's absolute build tokens and times were not given.

## 3. Anthropic "Contextual Retrieval" (Sept 2024): contextual chunk headers, contextual BM25, reranking, and which configuration produced each number

### Takeaway
All three headline reductions (35%, 49%, 67%) include contextual embeddings. Adding contextual BM25 on top of contextual embeddings moved the top-20 failure rate from 3.7% to 2.9%. Neither the blog nor the cookbook publishes a number for contextual BM25 alone, or even plain BM25 alone. The context headers cost $1.02 per million document tokens with Claude 3 Haiku and prompt caching, which fits an index-time background job.

### Cited Findings
- **Method:** Claude 3 Haiku is given the whole document plus one chunk and asked for "a short succinct context to situate this chunk within the overall document" (usually 50–100 tokens). This context is prepended to the chunk before embedding ("Contextual Embeddings") and before BM25 indexing ("Contextual BM25"). Prompt caching loads each document once — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- **Cost:** "$1.02 per million document tokens", assuming 800-token chunks, 8k-token documents, 50 tokens of instructions, and 100 tokens of context per chunk — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- **Reported reductions in top-20 retrieval failure (1 − recall@20), each against a 5.7% baseline, with Gemini Text 004 embeddings** — [Anthropic](https://www.anthropic.com/news/contextual-retrieval):
  - Contextual Embeddings alone: −35% (5.7% → 3.7%).
  - Contextual Embeddings + Contextual BM25: −49% (5.7% → 2.9%).
  - The same plus reranking (top 150 reranked to top 20 with Cohere): −67% (5.7% → 1.9%).
- **Setup:** domains were codebases, fiction, ArXiv papers, and science papers. Voyage and Gemini were the best embeddings tested. Passing 5, 10, and 20 chunks was compared, and 20 was best. BM25 is there for exact matches such as the identifier "TS-999". BM25 and embedding results are merged by rank fusion with deduplication; the weights and exact method are not given. There is no contextual-BM25-only figure — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- **When to skip retrieval:** for a knowledge base "smaller than 200,000 tokens (about 500 pages of material)", put all of it in the prompt; prompt caching cuts latency by more than 2× and cost by up to 90% — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- **Cookbook evaluation (codebases):** 9 codebases split into 737 chunks, 248 queries, voyage-2 embeddings; BM25 via Elasticsearch (English analyzer, `elasticsearch:9.2.0`). Pass@5 / @10 / @20 from the output cells:
  - Basic RAG: 80.92 / 87.15 / 90.06%.
  - Contextual embeddings: 88.12 / 92.34 / 94.29%.
  - Contextual embeddings + contextual BM25 hybrid: 88.86 / 92.31 / 95.23%.
  - Contextual embeddings + Cohere `rerank-english-v3.0` over k×10 candidates: 92.15 / 95.26 / 97.45%.

  — [Cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/contextual-embeddings/guide.ipynb)
- **Cookbook hybrid details:** each retriever returns its top 150; scores are fused as weight × 1/(rank+1), with semantic weight 0.8 and BM25 weight 0.2. The share of returned results that came from BM25 was 45.4% at k=5, 42.4% at k=10, and 39.2% at k=20. No BM25-only or contextual-BM25-only Pass@k is reported. The notebook's markdown summary row for the hybrid (86.43 / 93.21 / 94.99) does not match its output cell — [Cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/contextual-embeddings/guide.ipynb)
- **Cookbook contextualization run:** 737 chunks, 5 threads, 5 min 32 s. Tokens: 1,223,730 uncached input, 58,161 output, 176,079 written to cache, 2,267,069 read from cache ("61.83% of all input tokens used were read from cache"). Cost on an earlier Haiku: ~$9.20 without caching vs ~$2.85 with it ("69% savings"). Reranking is estimated (not measured) to add ~100–200 ms per query — [Cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/capabilities/contextual-embeddings/guide.ipynb)

### Inferences
- **The marginal value of contextual BM25 is small.** On top of contextual embeddings it cut failures by 0.8 points absolute, about 22% relative (3.7% → 2.9%). In the cookbook the hybrid changed Pass@20 by +0.94 and Pass@10 by −0.03. The documented evidence is for contextual BM25 as a complement to embeddings. Its standalone value for a BM25-only system is unmeasured, and the target would have to measure it on its own blind eval.
- **The mechanism does transfer to lexical retrieval.** The header adds document-level terms (project, file, section, entity names, date) that a chunk lacks, which is exactly the vocabulary-mismatch problem BM25 has. Much of that context is already structured metadata for records (subjects, type, date, session title), and can be prepended deterministically with no LLM. Raw session-log chunks would need a Haiku background pass. At the blog's Claude 3 Haiku pricing, a ~161k-token transcript corpus costs about $0.16. Current Haiku prices are higher and were not checked here.
- **Per-chunk call count suits background jobs.** The cookbook's 737 chunks took 332 s with 5 threads: about 0.45 s of wall time per chunk overall, or about 2.25 s per call on each thread.
- **The 200k-token guidance is a design check.** Below that size, Anthropic's own advice is to skip retrieval and load everything. It applies directly to a project whose curated notes fit in context.
- **Verdict.**
  - Contextual BM25: index ✔ (LLM in background, ~50–100 tokens per chunk). Query ✔ (plain BM25, no change).
  - Contextual embeddings: ✗ (embeddings).
  - Reranking: ✗ (cross-encoder API at query time, ~100–200 ms estimated, and not stdlib).

### Gaps
- No contextual-BM25-only or BM25-only failure rate in either the blog or the cookbook.
- No per-domain breakdown (codebases vs fiction, etc.) was extracted from the blog's charts.
- The blog's fusion method and weights are unspecified (the cookbook uses 0.8/0.2 weighted 1/(rank+1)).
- The cookbook's own tables disagree (the markdown summary does not match the output cells).

## 4. Fusion and query-side methods: reciprocal rank fusion, BM25 + graph score fusion, BM25F field weighting, doc2query / doc2query--, query decomposition and multi-query, HyDE, LLM reranking (RankGPT)

### Takeaway
Reciprocal rank fusion (k = 60) is model-free; it beat the best input system by about 4–5% MAP in Cormack's TREC tests and is the obvious way to combine BM25 with graph or other rankings. doc2query-- is the best-documented lexical-only gain: BM25 RR@10 on MS MARCO dev goes from 0.185 to 0.323, with all model work done at index time. HyDE, query2doc, decomposition (IRCoT), and RankGPT all need LLM calls at query time; RankGPT takes 10 calls and about 11–32 s per query. They fit the target only when the calling agent does the rewriting or reranking itself.

### Cited Findings
- **RRF formula:** RRFscore(d) = Σ_r 1/(k + r(d)), with "k = 60 … fixed during a pilot investigation and not altered during subsequent validation". The constant k "mitigates the impact of high rankings by outlier systems" — [Cormack et al. 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- **RRF sensitivity to k (pilot, 30 system runs, TREC topics 351–400):** MAP .2072 at k=0, .2134 at 20, .2145 at 60, .2147 at 80, .2098 at 500. For comparison, the best single system scored .2016, Condorcet .2074, CombMNZ .2039 — [Cormack et al. 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- **RRF on submitted TREC runs (MAP; RRF / best individual / Condorcet / CombMNZ):** Robust04 .3686 / .3586 / .3652 / .3575; TREC 3 .4350 / .4226 / .4256 / .4381; TREC 5 .3394 / .3165 / .3213 / .3237; TREC 9 .2830 / .3519 (human-in-the-loop; .2801 automated) / .2750 / .2671 — [Cormack et al. 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- **RRF on LETOR 3 (fusing learning-to-rank baselines):** RRF 0.6051, CombMNZ 0.6107 (difference not significant, p≈.2), Condorcet 0.5917, best individual ListNet 0.5846. The paper's summary: "RRF outperforms Condorcet, CombMNZ and the best system by 4% to 5% on average". RRF needs no score calibration and "ranks may be computed and summed one system at a time" — [Cormack et al. 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- **BM25 + graph fusion, published patterns:** (a) HippoRAG 1 averages min-max-normalized HippoRAG and retriever scores when linking confidence is low, which helped HotpotQA but sometimes hurt 2Wiki ([HippoRAG](https://arxiv.org/html/2405.14831)); (b) HippoRAG 2 fuses inside PPR, with passage-node restart weights = retriever similarity × 0.05 alongside phrase seeds ([HippoRAG 2](https://arxiv.org/html/2502.14802)); (c) context-level integration of RAG and GraphRAG gave +6.4% ([RAG vs GraphRAG](https://arxiv.org/html/2502.11371)).
- **BM25F (Robertson, Zaragoza, Taylor, CIKM 2004):** combining per-field BM25 scores linearly can perform poorly because it breaks BM25's non-linear term-frequency saturation. BM25F instead weights term frequencies per field before saturation; a title weighted 2 behaves like the title text appearing twice — [webis anthology](https://ir.webis.de/anthology/2004.cikm_conference-2004.6). Implementations differ: Terrier's BM25F follows a Zaragoza TREC-2004 per-field-normalized formulation, unlike the CIKM paper — [Terrier docs](https://javadoc.io/static/org.terrier/terrier-core/5.6/org/terrier/matching/models/BM25F.html); MG4J warns the definition "contains many subtleties" — [MG4J](https://mg4j.di.unimi.it/docs/it/unimi/di/mg4j/search/score/BM25FScorer.html)
- **doc2query-- method (ECIR 2023):** the T5 Doc2Query model's released 80 generated queries per passage are scored with a relevance model and only those above a threshold are appended (keeping the top 30% means t = 3.215 for ELECTRA). Filters tested were ELECTRA, MonoT5, and TCT-ColBERT. Filters based on the generator's own probabilities "were ineffective". Retrieval is BM25 on PISA, with k1, b, and stopwords tuned for every system — [doc2query--](https://arxiv.org/abs/2301.03266)
- **doc2query-- results (Table 1; RR@10 Dev / Dev2; nDCG@10 DL19 / DL20; latency; index size):**
  - BM25: 0.185 / 0.182; 0.499 / 0.479; 5 ms; 0.71 GB.
  - Doc2Query n=80: 0.279 / 0.267; 0.627 / 0.605; 30 ms; 1.41 GB.
  - Doc2Query n=80 with ELECTRA filter keeping 30%: 0.323 / 0.316 (Eval 0.325); 0.670 / 0.614; 23 ms; 0.95 GB.
  - Filtering is +16% RR@10 over unfiltered, with a 33% smaller index and 23% lower latency. The DL19/DL20 differences are not statistically significant.

  — [doc2query--](https://arxiv.org/abs/2301.03266)
- **doc2query-- compute:** filtering adds up to 78% GPU time (at n=10). At an equal GPU budget the filtered index still wins by 4% (34 GPU-hours) to 12% (216 GPU-hours) RR@10. Unfiltered Doc2Query needs 2.9× or more GPU time to match the filtered effectiveness — [doc2query--](https://arxiv.org/abs/2301.03266)
- **docT5query out of domain (BEIR, 18 datasets):** average +1.6% over BM25, and it "outperforms BM25 on 11/18 datasets". CPU latency 30 ms vs BM25's 20 ms; index 0.4 GB (DBPedia, 1M docs) — [BEIR](https://arxiv.org/html/2104.08663)
- **Query2doc:** pseudo-documents generated by few-shot LLM prompting expand the query, "boost[ing] the performance of BM25 by 3% to 15%" on MS MARCO and TREC DL without fine-tuning — [Query2doc](https://arxiv.org/abs/2303.07678)
- **HyDE:** InstructGPT (text-davinci-003, temperature 0.7, "write a paragraph that answers the question") writes hypothetical documents, which unsupervised Contriever embeds.
  - nDCG@10: DL19 61.3 vs BM25 50.6 vs Contriever 44.5; DL20 57.9 vs 48.0 vs 42.1. Recall@1k on DL19: 88.0 vs 75.0. The fine-tuned ContrieverFT reaches 62.1 on DL19.
  - BEIR nDCG@10, HyDE vs BM25: SciFact 69.1 vs 67.9, ArguAna 46.6 vs 39.7, TREC-COVID 59.3 vs 59.5, FiQA 27.3 vs 23.6, DBPedia 36.8 vs 31.8, TREC-NEWS 44.0 vs 39.5.

  — [HyDE](https://arxiv.org/pdf/2212.10496)
- **Iterative decomposition with BM25 (IRCoT + BM25, an LLM at every step):** R@5 MuSiQue 44.7 vs single-step BM25 41.2; 2Wiki 75.6 vs 61.9; HotpotQA 79.0 vs 72.2. IRCoT costs $1–3 and 20–40 min per 1,000 queries (GPT-3.5) — [HippoRAG](https://arxiv.org/html/2405.14831)
- **RankGPT setup and quality:** listwise "permutation generation" over the BM25 top 100, with a sliding window of 20 and step 10. nDCG@10 on DL19 / DL20 / BEIR average: BM25 50.58 / 47.96 / 43.42; monoT5-3B 71.83 / 68.89 / 51.36; Cohere Rerank-v2 73.22 / 67.08 / 49.45; gpt-3.5-turbo 65.80 / 62.91 / 49.37; gpt-4 75.59 / 70.56 / 53.68. On BEIR, gpt-4 reranks only the top 30 from gpt-3.5 — [RankGPT](https://arxiv.org/html/2304.09542)
- **RankGPT cost per query:**
  - gpt-3.5-turbo: 19,960 tokens over 10 requests, $0.040, about 1.1 s per call (~11 s per query).
  - gpt-4: 19,890 tokens, $0.596, about 3.2 s per call (~32 s per query).
  - gpt-4 reranking the top 30 only: 3,271 tokens, 1 request, $0.098.

  The whole GPT-4 experiment cost $556 — [RankGPT](https://arxiv.org/html/2304.09542)
- **RankGPT pointwise vs listwise and distillation:**
  - With davinci-003 on DL19 (nDCG@10): pointwise relevance generation 50.58, query generation 45.37, listwise permutation 61.50.
  - A 435M DeBERTa distilled from ChatGPT permutations reaches BEIR average 53.03 vs monoT5-3B's 51.36. The abstract says 440M.
  - Distillation data (10k queries) cost about $40.

  — [RankGPT](https://arxiv.org/html/2304.09542)
- **Cross-encoder reranking cost:** BM25 + cross-encoder reranking is +11% over BM25 on average on BEIR, but takes 6,100 ms on CPU (450 ms on GPU) per query on DBPedia (1M docs), against 20 ms for BM25 — [BEIR](https://arxiv.org/html/2104.08663)

### Inferences
- **RRF fits trivially:** no model, O(list length), ✔ in stdlib.
  - With k=60, rank 1 scores 1/61 ≈ 0.0164 and rank 20 scores 1/80 = 0.0125. A document at rank 20 in both lists (0.025) therefore beats a document at rank 1 in only one list. Fusing BM25 with a graph list rewards agreement, but graph-only finds are hard to surface.
  - A weighted RRF (as in the cookbook's 0.8/0.2) or a small reserved quota for graph-only items are the obvious knobs. Neither is tested for this use case.
  - Cormack's pilot shows k anywhere between 20 and 100 changes MAP by less than 0.002, so k needs no tuning.
- **BM25F fits structured records.** Fields such as subjects, statement, why, type, and session title can be weighted before saturation, ✔ with no model. No numeric gains were extracted here. SQLite FTS5's `bm25()` column weights enter the phrase frequency in a similar way (section 6).
- **doc2query-- is the cleanest fit for the constraint.** All the work is at index time and the query side is plain BM25.
  - In the target, a Haiku background job could generate likely questions per record or chunk. A lexical stand-in for the ELECTRA filter is a self-retrieval check: keep a generated question only if BM25 ranks its source record in the top k. **This is untested.**
  - The paper's central warning applies: unfiltered generations add hallucinated terms that hurt, and its gains are in-domain (MS MARCO-trained T5). Out of domain, docT5query's average gain shrinks to +1.6%.
  - Expansion adds matching terms, so it may also raise false hits on questions whose answer is not in memory. Abstention accuracy should be checked.
- **Query rewriting is free when the agent does it.** In a coding agent, the caller is already an LLM writing the search call. HyDE, query2doc, multi-query, and decomposition can be done by the agent in that same call: it writes alternative phrasings or a hypothetical answer, and the script runs several BM25 queries and fuses them with RRF. This adds no extra LLM call to the retrieval process and costs only a few milliseconds per extra BM25 query (section 6).
  - The closest published evidence for "LLM-written pseudo-answer appended to a BM25 query" is query2doc's +3–15%. HyDE's +10.7 nDCG@10 on DL19 used a dense encoder, not BM25.
  - IRCoT's BM25 gains (+13.7 R@5 on 2Wiki) correspond to the agent iterating searches across turns.
- **RankGPT cannot fit 0.5 s** (10 calls, 11–32 s per query). The equivalent in an agent is the agent reading the top 20 itself, which is listwise reranking at no extra call cost. The 435M distilled reranker needs a local transformer, so it isn't stdlib either.
- **Verdict.**
  - RRF ✔. BM25F ✔. doc2query-- ✔ (index-time LLM in background, query-time BM25).
  - HyDE, query2doc, multi-query, decomposition: ✗ inside the retrieval process; ✔ if performed by the calling agent.
  - RankGPT ✗. Cross-encoder reranking ✗.

### Gaps
- No numeric BM25F gains (the CIKM 2004 full text was not read).
- No published result fusing BM25 with PPR or graph scores by RRF; only the HippoRAG patterns above.
- No numbers for LLM-generated doc2query (GPT or Claude as generator) in the sources read.
- HyDE with a BM25 back end is not in the tables read.
- Specific decomposition methods (Self-Ask, least-to-most, RAG-Fusion) were not researched; IRCoT data comes only from the HippoRAG paper.

## 5. Lexical-only methods that close part of the gap to dense retrieval: document expansion, SPLADE with a precomputed index, pseudo-relevance feedback (RM3), character n-grams

### Takeaway
On MS MARCO dev, BM25's RR@10 of 0.184 rises to:
- 0.277 with docT5query expansion;
- 0.323 with filtered doc2query--;
- 0.322 with SPLADE-doc, which has no query encoder, so every weight is precomputed and query time is a bag-of-words lookup;
- 0.368 with DistilSPLADE-max and 0.383–0.400 with SPLADE++/SPLADE-v3, both of which need a neural query encoder.

Out of domain (BEIR), document expansion's average gain shrinks to +1.6%. RM3 raises recall and MAP on deep-judged TREC DL but lowers MS MARCO dev RR@10 by about 15%.

### Cited Findings
- **SPLADE v2 table (MS MARCO dev MRR@10 / R@1000; TREC DL19 nDCG@10 / R@1000)** — [SPLADE v2](https://arxiv.org/pdf/2109.10086):
  - Sparse: BM25 0.184 / 0.853; 0.506 / 0.745. DeepCT 0.243 / 0.913; 0.551 / 0.756. doc2query-T5 0.277 / 0.947; 0.642 / 0.827. DeepImpact 0.326 / 0.948; 0.695. COIL-tok 0.341 / 0.949; 0.660.
  - SPLADE family: SPLADE 0.322 / 0.955; 0.665 / 0.813. SPLADE-max 0.340 / 0.965; 0.684 / 0.851. **SPLADE-doc 0.322 / 0.946; 0.667 / 0.747.** DistilSPLADE-max 0.368 / 0.979; 0.729 / 0.865.
  - Dense: TAS-B 0.347 / 0.978; 0.717 / 0.843. TCT-ColBERT 0.359 / 0.970; 0.719 / 0.760.
- **SPLADE-doc definition:** there is "no query expansion nor query term weighting"; the score is the sum of the document's term weights over the query's tokens. "Because the ranking score solely depends on the document term weights, everything can be pre-computed offline". The vocabulary is BERT's (|V| = 30,522). The paper also reports results "on par with approaches like doc2query-T5 (e.g. MRR@10=29.6 for a model with an average of 19 non-zero weights per document)" — [SPLADE v2](https://arxiv.org/pdf/2109.10086)
- **Current SPLADE models need a query encoder at search time** (PyTorch or ONNX `--encoder` in Pyserini). Dev RR@10 / DL19 nDCG@10: SPLADE++ EnsembleDistil 0.3828 / 0.7308; SPLADE++ SelfDistil 0.3776 / 0.7358; SPLADE-v3 0.4000 / 0.7264 (DL20 0.7522) — [Pyserini 2CR](https://castorini.github.io/pyserini/2cr/msmarco-v1-passage.html)
- **RM3 and Rocchio (Pyserini, k1=0.9, b=0.4; DL19 AP / nDCG@10 / R@1k; DL20 nDCG@10; Dev RR@10 / R@1k)** — [Pyserini 2CR](https://castorini.github.io/pyserini/2cr/msmarco-v1-passage.html):
  - BM25: 0.3013 / 0.5058 / 0.7501; 0.4796; 0.1840 / 0.8526.
  - BM25+RM3: 0.3416 / 0.5216 / 0.8136; 0.4896; 0.1566 / 0.8606.
  - BM25+Rocchio: 0.3474 / 0.5275 / 0.8007; 0.4910; 0.1595 / 0.8620.
  - Tuned BM25 (k1=0.82, b=0.68): Dev RR@10 0.1875; with RM3 0.1646.
- **RM3 on top of document expansion (BM25 on doc2query-T5-expanded docs, k1=0.9, b=0.4):** Dev RR@10 0.2723 without RM3 and 0.2139 with it. DL19 nDCG@10 0.6417 → 0.6586; R@1k 0.8310 → 0.8863 — [Pyserini 2CR](https://castorini.github.io/pyserini/2cr/msmarco-v1-passage.html)
- **Out-of-domain (BEIR) averages relative to BM25:** docT5query +1.6%, DeepCT −27.9%, SPARTA −20.3%, ANCE −7.4%, TAS-B −2.8%, DPR −47.7%, ColBERT +2.5%, BM25 + cross-encoder +11%. "BM25 is a robust baseline"; in-domain on MS MARCO, BM25 "heavily underperforms neural approaches by 7-18 points" — [BEIR](https://arxiv.org/html/2104.08663)
- **Tokenization and parameters move BM25 by about 1–2 nDCG points on BEIR:**
  - Snowball stemming raises the average nDCG@10 from 38.4 to 39.7 (stopwords removed in both).
  - Lucene with k1=0.9, b=0.4 averages 41.1, against 39.9 with k1=1.2, b=0.75.
  - Elasticsearch averages 42.0, which the authors attribute to tokenization differences.

  — [BM25S](https://arxiv.org/html/2407.03618)
- **Summary nodes as document-side expansion:** BM25 retrieval over RAPTOR's tree raised NarrativeQA ROUGE from 23.52 to 27.93 — [RAPTOR](https://arxiv.org/html/2401.18059)
- **Character trigrams in stdlib:** SQLite FTS5's `trigram` tokenizer "treats each contiguous sequence of three characters as a token, allowing FTS5 to support more general substring matching", including indexed LIKE/GLOB. Substrings shorter than 3 characters match nothing. The `porter` tokenizer adds English stemming — [SQLite FTS5](https://www.sqlite.org/fts5.html)

### Inferences
- **Document expansion is the lexical method with the strongest evidence, and it moves all model cost to index time**, which matches the constraint. In-domain, doc2query-- (0.323) and SPLADE-doc (0.322) close roughly three-quarters (about 74–85%) of the gap between BM25 (0.184) and strong dense models (0.347–0.370). That is the best a precomputed lexical index has shown.
- **Using an LLM as the generator is untested in these sources.** Replacing T5 with an LLM such as Haiku is not evaluated here. Query2doc shows LLM-written text helps BM25 from the query side (+3–15%).
- **SPLADE-doc is the one SPLADE variant that fits the query-time constraint.** At query time it needs only WordPiece tokenization (implementable in stdlib with the 30,522-entry vocab) and postings lookups. At index time it needs a BERT-size masked-LM forward pass per chunk. That is a local PyTorch/ONNX dependency, neither stdlib nor an LLM API call, and the model was trained on MS MARCO, so domain shift to project memory is likely. Verdict: query ✔, index ✗ under a strict stdlib rule.
- **RM3 and Rocchio are model-free and cheap** (a second BM25 pass), but they cut top-rank precision on MS MARCO dev by about 12–15%, and on expanded documents too (−21%), while raising deep recall. For an agent that reads only the top ~10 hits, PRF is likely a net loss, except possibly for recall-oriented "list all X" queries. Verdict: ✔ feasible, likely not worth it as a default.
- **Character n-grams have no quality evidence in these sources.** For subject-name variants (`ran-rl`, `ran_rl`, `RanRL`), identifier splitting plus case folding and light stemming should cover most cases. A trigram field used only for fuzzy subject linking (e.g. a second FTS5 table or a BM25F field) is plausible but unmeasured. Stemming alone was worth +1.3 nDCG@10 on BEIR.
- **Parameter note.** BM25S's BEIR averages favour lower b (0.4) over Lucene's default 0.75. That is consistent with the b≈0.5 already used by the target. SQLite FTS5 hard-codes k1=1.2 and b=0.75 (section 6).

### Gaps
- SPLADE-doc's BEIR (zero-shot) numbers were not extracted.
- The RM3 parameters behind the Pyserini rows (fbTerms, fbDocs, original query weight) were not extracted.
- No quality evidence found for character-n-gram BM25 on entity or identifier matching.
- No source read reports LLM-generated document expansion (e.g. InPars-style or GPT/Claude doc2query) with BM25.

## 6. Practical: pure-Python BM25 over ~10k–100k chunks, inverted-index caching and incremental updates, and PPR on graphs with ~10^4 nodes

### Takeaway
Pure-Python BM25 is fast enough at 10k–100k chunks, provided it uses an inverted index. The popular `rank_bm25` does not use one, which explains its 4.46 queries per second at 57k documents. In local measurements, scoring a query took under 1.5 ms (p95) for 6-term content queries, and up to ~50 ms (p95) at 100k chunks when stopword-like terms were included. In a process-per-query CLI, the real bottleneck is loading the index: a marshalled dict-of-lists took 0.65–5.8 s, packed arrays 0.09–0.20 s. stdlib `sqlite3` FTS5 avoided load cost entirely (~85–95 ms for a new process with a warm OS page cache). PPR by full power iteration took ~0.26–0.33 s on 10^4 nodes; forward push took under 1 ms.

### Cited Findings
- **BM25S design:** "an efficient Python-based implementation of BM25 that only depends on Numpy and Scipy", computing BM25 scores eagerly at index time and storing them in sparse matrices, so a query just slices token rows and sums them. It reports "over 100x higher throughput in 10 out of the 14 datasets" and up to 500×, single-threaded on a Kaggle Intel Xeon @ 2.20GHz with 30 GB RAM — [BM25S](https://arxiv.org/html/2407.03618)
- **Throughput in queries/s (BM25S / Elasticsearch / rank_bm25), with corpus sizes from BEIR** — QPS from [BM25S](https://arxiv.org/html/2407.03618); sizes from [BEIR](https://arxiv.org/html/2104.08663):
  - NFCorpus (3,633 docs): 1196.16 / 45.84 / 224.66.
  - SciFact (5,183): 952.92 / 20.81 / 47.60.
  - ArguAna (8,674): 573.91 / 13.67 / 2.00.
  - SCIDOCS (25,657): 767.05 / 17.93 / 9.01.
  - FiQA (57,638): 507.03 / 16.96 / 4.46.
  - TREC-COVID (171,332): 85.64 / 7.34 / 1.48.
  - Quora (522,931): 183.53 / 21.80 / 1.18.
  - MS MARCO (8,841,823): 12.20 / 11.88 / 0.07.
- **Why rank_bm25 is slow:** `BM25Okapi.get_scores` runs `q_freq = np.array([(doc.get(q) or 0) for doc in self.doc_freqs])` for every query term. That is a Python loop over every document, with no inverted index — [rank_bm25 source](https://github.com/dorianbrown/rank_bm25/blob/master/rank_bm25.py)
- **Engine-backed BM25 latency:** 20 ms on CPU with a 0.4 GB index for DBPedia (1M docs) — [BEIR](https://arxiv.org/html/2104.08663)
- **SQLite FTS5 `bm25()`:**
  - k1 and b are "hard-coded at 1.2 and 0.75". Scores are negated so that `ORDER BY bm25(t)` (or `ORDER BY rank`) returns best matches first.
  - Extra arguments give per-column weights that scale per-column occurrence counts inside the phrase frequency.
  - Each committed transaction writes a new b-tree segment; segments are merged incrementally (`automerge`, default 4; `crisismerge`, default 16) or all at once by `optimize`, which "can take a long time to run".

  — [SQLite FTS5](https://www.sqlite.org/fts5.html)
- **HippoRAG's PPR:** python-igraph (C) on 2× AMD EPYC 7513, over graphs of 42k–92k phrase nodes. End-to-end online retrieval, including the LLM NER call, takes ~3 min per 1,000 queries — [HippoRAG](https://arxiv.org/html/2405.14831)
- **Graph density per 10k corpus tokens:** HippoRAG2's graphs have about 523 nodes and 2,310 edges (novel) and 598 nodes and 3,979 edges (medical) — [GraphRAG-Bench](https://arxiv.org/html/2506.05690)

### Inferences
- **Local measurement setup (not a published result).** `/usr/bin/python3` 3.9.6 on an Intel Core i9-9880H @ 2.3 GHz Mac. Script: `research_notes/Coding agent memory techniques/bench/bench_retrieval.py`; raw output in `bench/bench_output_2026-11-04.txt`.
  - Corpus: synthetic Zipf text (50k-term vocabulary, exponent 1.07, about 80 tokens per chunk).
  - Index: BM25 weights (k1=0.9, b=0.4) precomputed per posting (BM25S-style). Two layouts: a dict of Python lists, and packed `array('i')` doc IDs + `array('f')` weights with a term→(offset, length) dict.
  - Queries: 200, top 20 via `heapq.nlargest`. "Typical" = 6 terms drawn from frequency ranks 50–20,000. "Heavy" = the same plus 2 terms from the top-20 ranks (stopword-like).
  - Results:

| chunks | postings | build | typical query mean / p95 | heavy query mean / p95 | load: marshal dict-of-lists | load: packed arrays |
|---|---|---|---|---|---|---|
| 10,000 | 576,618 | 0.7 s | 0.1 / 0.2 ms | 2.7 / 4.2 ms | 0.65 s (9 MB) | 0.09 s (5 MB) |
| 50,000 | 2,881,385 | 3.6 s | 0.3 / 1.0 ms | 15.5 / 22.9 ms | 2.92 s (41 MB) | 0.13 s (24 MB) |
| 100,000 | 5,761,635 | 7.3 s | 0.4 / 1.4 ms | 35.4 / 48.7 ms | 5.80 s (82 MB) | 0.20 s (47 MB) |

  Query times on the packed index were the same within noise (100k: typical 0.4 / 1.5 ms, heavy 34.2 / 47.1 ms). Starting the interpreter took a median 75 ms (`python3 -c pass`) or 53 ms (`-I -S`). Peak RSS for the whole run was 562 MB. pickle was not measured.
- **Local measurement: stdlib `sqlite3` FTS5** (SQLite 3.51.0 bundled with this Python; script `bench/bench_fts5.py`; same synthetic chunks; 2 columns; OR-query; `ORDER BY bm25(t, 2.0, 1.0) LIMIT 20`). The "cold process" column means a new interpreter, but it ran right after the build, so the OS page cache was warm; a true cold start would be slower:

| chunks | build | db size | typical query mean / p95 | heavy query mean / p95 | new process, page cache warm (start + open + 1 query) |
|---|---|---|---|---|---|
| 10,000 | 0.2 s | 8 MB | 1.0 / 2.7 ms | 26.3 / 36.0 ms | 85 ms |
| 100,000 | 3.4 s | 76 MB | 5.2 / 20.9 ms | 392 / 512 ms | 95 ms |

- **Reading the measurements.**
  - Query scoring is never the bottleneck for content-word queries at this scale.
  - Stopword-like terms make cost grow with posting length: 35 ms in pure Python at 100k chunks, and 392 ms in FTS5, which evaluates `bm25()` for every matching row before `LIMIT`. Stopword removal (or AND semantics) is mandatory for FTS5 at 100k.
  - In a process-per-query CLI, the index format decides whether 0.5 s is met. A marshalled dict-of-lists blows the budget at about 10k chunks (0.65 s). Packed arrays load in 0.09–0.20 s, so startup (~0.05–0.08 s) + load + query stays under 0.35 s even at 100k chunks.
  - FTS5 reads pages on demand, so it has no load step (85–95 ms for a new process with a warm OS page cache). It also gives incremental, crash-safe updates for free. Its costs are a fixed k1/b, no custom scoring without C, and availability that depends on how SQLite was compiled (it was present here).
- **Incremental updates for a pure-Python index.** Eager weights depend on N and avgdl, so append-only stores would need a full recompute on every write. Alternatives:
  - Store raw tf and document lengths and compute BM25 at query time. This adds a few arithmetic operations per posting; not measured.
  - Keep a frozen main index plus a small delta segment that is rebuilt on each write and merged periodically. This is the same segment-and-merge idea FTS5 documents.
- **Local measurement: PPR in pure Python** (`bench/bench_retrieval.py`). Graph: random, with heavy-tailed degrees; edges stored in both directions, weight 3 for 20% (typed relations) and 1 otherwise. 4 random seeds per query, 20 queries, damping 0.5 (probability of following an edge, as in igraph/HippoRAG). Results:

| graph | power iteration to L1 < 1e-6 | forward push ε=1e-4 | forward push ε=1e-6 |
|---|---|---|---|
| 10k nodes, ~50k edges | mean 258 ms, max 356 ms, 14–15 iterations | 0.3 ms mean (max 0.6); 41–69 nodes get mass | 25.3 ms mean (max 32.4); 2,885–4,996 nodes |
| 10k nodes, ~100k edges | 333 ms, max 441 ms, 11–12 iterations | 0.4 ms (max 0.6); 37–64 nodes | 28.1 ms (max 41.4); 2,037–3,209 nodes |
| 30k nodes, ~300k edges | 1,178 ms, max 1,312 ms, 12 iterations | 0.6 ms (max 1.2); 36–67 nodes | 23.2 ms (max 33.6); 1,522–2,355 nodes |

- **Reading the PPR numbers.**
  - With damping 0.5, half the mass returns to the seeds at every step, so mass decays by half per hop. Andersen–Chung–Lang forward push therefore touches only the seeds' neighbourhood and stays at about 1 ms (ε=1e-4) to about 30 ms (ε=1e-6), independent of graph size.
  - Full power iteration in CPython costs about 0.3 s at 10^4 nodes and over 1 s at 3×10^4. That is too slow once load time is added. HippoRAG relied on igraph's C implementation.
  - Graph load time was not measured; the same packed-array approach applies (CSR offsets + neighbour array + weight array).
- **Verdict.** BM25 over 10k–100k chunks ✔ in stdlib under 0.5 s with an inverted index and either a packed-array cache or FTS5 (with stopword removal). PPR over ~10^4 nodes ✔ with forward push; borderline-to-✗ with full power iteration in pure Python.

### Gaps
- No published benchmark of a stdlib-only BM25. BM25S needs numpy/scipy, and rank_bm25 has no inverted index. The only stdlib numbers here are the local synthetic runs above, which used Zipf text, not real chunks, and excluded tokenization cost.
- No published pure-Python PPR timings; local only.
- Not measured: pickle load times, lazy (query-time) BM25 weighting, graph-cache load time, and FTS5 with the porter or trigram tokenizers.
- Not verified: which other Python/SQLite builds (e.g. python.org installers, Linux distributions) ship with FTS5 enabled.

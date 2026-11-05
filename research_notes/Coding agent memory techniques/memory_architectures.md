# Long-term memory architectures for LLM agents (2023–2026): what they store, how they write, update and retrieve, and what they gain or lose

Source labels used in every bullet:
- **[peer-reviewed]**: venue confirmed in the fetched text.
- **[academic preprint]**: arXiv, no confirmed venue.
- **[vendor]**: written by the company that sells the system.
- **[competitor re-run]**: one system's numbers measured by another system's authors.
- **[independent benchmark]**: benchmark authors who don't sell any of the systems they test.
- **(computed)**: arithmetic I did on the cited numbers.

Unless stated otherwise, "J" means the LLM-as-a-judge accuracy in % on LoCoMo.

## 1. Zep / Graphiti: bi-temporal knowledge graph (episodes, entities, communities, edge invalidation) and its DMR / LongMemEval results

### Takeaway
Zep keeps the raw messages ("episodes") as a lossless store. Over them it builds an LLM-extracted graph of entities and facts, with four timestamps on every edge, and it marks contradicted facts invalid instead of deleting them. Its own results (vendor, Jan 2025) are saturated on DMR (Zep 94.8% vs full-conversation 94.4% on gpt-4-turbo). On LongMemEval_S it scores 71.2% vs 60.2% for full context (gpt-4o), with ~90% lower latency (2.58 s vs 28.9 s) and 1.6k vs 115k context tokens. It loses to full context on questions about what the assistant itself said. Its LoCoMo score depends on who runs it: 59.22 to 79.09 J.

### Cited Findings
**What it stores (vendor, arXiv 20 Jan 2025)**
- Three subgraphs. (1) The **episode subgraph**: episodic nodes hold the raw input (messages, text or JSON) "as a non-lossy store", and episodic edges link each episode to the entities it mentions. (2) The **semantic entity subgraph**: entity nodes extracted from episodes and resolved against existing ones, plus semantic edges that hold facts between entities. (3) The **community subgraph**: clusters of strongly connected entities with high-level summaries — [Zep paper](https://arxiv.org/html/2501.13956)
- **Bi-temporal model.** Timeline T is event time, with `t_valid` / `t_invalid` (when the fact was true). Timeline T′ is ingestion (transaction) time, with `t′_created` / `t′_expired` (when the system added or invalidated it). All four timestamps are stored on edges — [Zep paper](https://arxiv.org/html/2501.13956)

**How it writes and updates**
- Entities are extracted from the current message plus the last n = 4 messages, and the speaker is always extracted. A Reflexion-inspired "reflection" step reduces hallucinations and improves coverage — [Zep paper](https://arxiv.org/html/2501.13956)
- **Entity resolution.** Names are embedded (1024-d). Duplicate candidates come from cosine search plus full-text search over names and summaries. An LLM entity-resolution prompt decides whether a node is a duplicate and writes the updated name and summary. Graph writes use predefined Cypher queries, not LLM-generated ones, "to keep the schema consistent and reduce hallucination" — [Zep paper](https://arxiv.org/html/2501.13956)
- **Facts (edges).** An LLM extracts facts between the given entities, each with an ALL-CAPS relation type. The same fact can be attached to several entity pairs (hyper-edges). Deduplication runs hybrid search restricted to edges between the same entity pair, then an LLM fact-resolution prompt — [Zep paper](https://arxiv.org/html/2501.13956)
- **Edge invalidation.** Absolute and relative dates are resolved against a reference timestamp `t_ref`. An LLM compares each new edge with semantically related existing edges. When the two contradict and overlap in time, the old edge's `t_invalid` is set to the new edge's `t_valid`. Ordering on T′ gives newer information priority — [Zep paper](https://arxiv.org/html/2501.13956)
- **Communities.** Zep uses label propagation (chosen over Leiden because it extends incrementally): a new entity joins the community held by the plurality of its neighbours, and the summaries are updated. The paper says periodic full refreshes are still needed because incremental communities drift. Summaries are built by iterative map-reduce, and community names are embedded — [Zep paper](https://arxiv.org/html/2501.13956)

**How it retrieves**
- The pipeline is f(α) = χ(ρ(φ(α))):
  - **Search φ:** cosine similarity over facts, entity names and community names; Okapi **BM25** full-text search (Neo4j's Lucene); and **breadth-first search** to n hops from seed nodes (e.g., recent episodes).
  - **Rerankers ρ:** RRF, MMR, episode-mentions (favours often-mentioned entities or facts), node distance (graph distance from a centroid node), and a cross-encoder (LLM, "highest cost").
  - **Constructor χ:** prints facts with their valid/invalid dates, entity names with summaries, and community summaries, inside FACTS / ENTITIES tags.
  - [Zep paper](https://arxiv.org/html/2501.13956)

**Reported results (vendor self-report, Jan 2025)**
- **DMR, Table 1** (MemGPT and recursive-summarization rows are taken from the MemGPT paper):

  | Model | Recursive summarization | Conversation summaries | MemGPT | Full conversation | Zep |
  |---|---|---|---|---|---|
  | gpt-4-turbo | 35.3% | 78.6% | 93.4% | 94.4% | 94.8% |
  | gpt-4o-mini | – | 88.0% | – | 98.0% | 98.2% |

  Zep could not reproduce MemGPT with gpt-4o-mini — [Zep paper](https://arxiv.org/html/2501.13956)
- Zep calls DMR inadequate: about 60 messages per conversation (fits in context), single-turn fact retrieval, and ambiguously phrased questions — [Zep paper](https://arxiv.org/html/2501.13956)
- **LongMemEval_S, Table 2** (~115k-token histories):

  | Model | System | Accuracy | Latency | Latency IQR | Context |
  |---|---|---|---|---|---|
  | gpt-4o-mini | Full context | 55.4% | 31.3 s | 8.76 s | 115k |
  | gpt-4o-mini | Zep | 63.8% | 3.20 s | 1.31 s | 1.6k |
  | gpt-4o | Full context | 60.2% | 28.9 s | 6.01 s | 115k |
  | gpt-4o | Zep | 71.2% | 2.58 s | 0.684 s | 1.6k |

  The stated "+15.2%" and "+18.5%" are relative gains. In absolute terms they are +8.4 and +11.0 points (computed). The paper claims a ~90% latency reduction — [Zep paper](https://arxiv.org/html/2501.13956)
- **Per question type, Table 3** (full context → Zep):

  | Question type | gpt-4o-mini | gpt-4o |
  |---|---|---|
  | single-session-preference | 30.0 → 53.3 | 20.0 → 56.7 |
  | **single-session-assistant** | **81.8 → 75.0 (−9.06% rel.)** | **94.6 → 80.4 (−17.7% rel.)** |
  | temporal reasoning | 36.5 → 54.1 | 45.1 → 62.4 |
  | multi-session | 40.6 → 47.4 | 44.3 → 57.9 |
  | knowledge-update | **76.9 → 74.4 (−3.36%)** | 78.2 → 83.3 |
  | single-session-user | 81.4 → 92.9 | 81.4 → 92.9 |

  The single-session-user row is identical for both models, which may be a transcription error in the paper — [Zep paper](https://arxiv.org/html/2501.13956)
- **Latency caveat.** Zep was queried from a residential laptop in Boston to AWS us-west-2. That network latency was absent from the full-context baseline — [Zep paper](https://arxiv.org/html/2501.13956)
- **Stated limitations.**
  - DMR retrieval is described inconsistently (top 10 vs 20 nodes/edges).
  - MemGPT could not be run on LongMemEval.
  - BFS and episode-to-fact traceability were not evaluated.
  - Less capable models may not understand Zep's temporal data.
  - Single-session-assistant is called "a notable exception that needs further work".
  - [Zep paper](https://arxiv.org/html/2501.13956)

**LoCoMo: four different numbers for Zep**
- **65.99 ± 0.16 J** in Mem0's run (gpt-4o-mini), with 3,911 context tokens and search p95 0.778 s [competitor re-run, Apr 2025] — [Mem0 paper](https://arxiv.org/html/2504.19413)
- **75.14% ± 0.17** in Zep's own corrected run, with search p95 0.632 s using concurrent search [vendor, 6 May 2025]. Zep blames Mem0's setup: both speakers were assigned the user role, timestamps were appended to message text instead of using `created_at`, and searches ran sequentially — [Zep rebuttal](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)
- **79.09 overall** in MIRIX's run (gpt-4.1-mini backbone, GPT-4.1 judge) [competitor re-run, Jul 2025] — [MIRIX paper](https://arxiv.org/html/2507.07957)
- **59.22 overall** in MemOS's run (gpt-4o-mini), with 2,701 tokens [competitor re-run, vendor MemTensor] — [MemOS paper](https://arxiv.org/html/2507.03724)
- Mem0 claims Zep's memory footprint exceeds 600k tokens per conversation, against ~26k for the raw conversation — [Mem0 paper](https://arxiv.org/html/2504.19413). Zep attributes Mem0's Zep results to the misconfiguration above — [Zep rebuttal](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)
- The rebuttal page also carries an update claiming "80% at under 200 ms", dated "December 9, 2015" (evidently a typo). The page metadata says it was last modified 2026-06-03 — [Zep rebuttal](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)

**Independent and third-party evaluations**
- **MemoryAgentBench** [independent benchmark, UCSD, first posted Jul 2025]. Zep scores: accurate retrieval 37.5, test-time learning 37.5, long-range understanding 16.2, selective forgetting 7.0 single-hop / 3.0 multi-hop, overall 24.0. Plain BM25 scores 41.5 overall and 60.5 on accurate retrieval — [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- **HaluMem** [Nov 2025, authors overlap with MemOS/MemTensor, see §5].
  - Memory updating: Zep is correct 47.28% / omits 52.31% on Medium, and 37.35% / 62.14% on Long.
  - QA correct: 55.47% (Medium) and 50.19% (Long).
  - There is no extraction score because Zep has no API that lists the memories extracted from a dialogue.
  - [HaluMem](https://arxiv.org/html/2511.03506)
- **MemOS's load test** [competitor re-run]. At 10 QPS, Zep search has mean 571.7 ms and P99 5,348.7 ms. At 40 QPS, Zep's success rate fell to 26.6% (add) and 26.8% (search) — [MemOS paper](https://arxiv.org/html/2507.03724)

### Inferences
- Zep is a "raw + derived" design. Raw episodes are kept, but the retrieval Zep evaluated returns only facts, entity summaries and community summaries (episode traversal was not evaluated). Its losses on single-session-assistant (−6.8 and −14.2 points, computed) fit a fact extractor centred on entities and the user, which drops what the assistant said.
- DMR is saturated (full conversation 94.4–98.0%), so neither MemGPT's nor Zep's DMR numbers say much about memory quality.
- The LongMemEval gain appears where the history (~115k tokens) is long enough to degrade full-context reading. The LongMemEval paper shows GPT-4o falling from 0.870 with oracle evidence to 0.606 with the full history (§7).
- **What transfers to a local, stdlib-only, no-embedding setting with <0.5 s retrieval:**
  - The bi-temporal fields: event-time `valid_from`/`valid_to` plus transaction-time `recorded_at`/`expired_at` on every record.
  - Invalidation by setting `valid_to` (append-only) instead of deleting.
  - Entity resolution by full-text name matching plus a background LLM check.
  - The BM25 half of the hybrid search, n-hop BFS over typed edges, and the RRF, MMR, episode-mention and node-distance rerankers. These are pure arithmetic and fast in Python.
  - The constructor format that prints each fact with its validity range.
  - Episodic edges (episode → entity), i.e. a pointer from extracted entities back to the raw message. The paper mentions episode-to-fact traceability but defers its evaluation to future work. In a records store, the equivalent is a `source {chat, line}` field on every fact.
- **What doesn't transfer:**
  - 1024-d embeddings and cosine search.
  - Cross-encoder reranking, which is a query-time LLM call and breaks the background-only rule and the 0.5 s budget.
  - Community summaries could be rebuilt offline, since label propagation is simple, but Zep itself reports drift under incremental updates.
  - Zep's own 2.58–3.20 s per query (remote service plus network) is far above 0.5 s; a local BM25 path is what this setting can actually run.

### Gaps
- I found no independent replication of Zep's LongMemEval numbers. The MemOS paper reuses Zep's own gpt-4o-mini numbers verbatim (identical per-type values: 53.3 / 75.0 / 54.1 / 47.4 / 74.4 / 92.9, overall 63.8) rather than re-running Zep — [MemOS paper](https://arxiv.org/html/2507.03724)
- There are no results for BFS or episode retrieval, the parts closest to "keep the raw text".
- The "80% at <200 ms" claim in the rebuttal's undated update can't be verified.
- I didn't check Graphiti's current GitHub/docs for changes after the Jan 2025 paper.

## 2. Mem0 and Mem0g: extraction pipeline, ADD/UPDATE/DELETE/NOOP, LoCoMo results, token and latency savings, and disputes

### Takeaway
Mem0 (vendor, 28 Apr 2025) stores LLM-extracted facts, not raw turns. Each candidate fact is reconciled against its 10 most similar memories by one LLM tool call that chooses ADD, UPDATE, DELETE or NOOP. Mem0g adds a Neo4j triplet graph that marks conflicting relations invalid instead of deleting them. Mem0's own table shows **full context beating both** (72.90 J vs 66.88 Mem0 and 68.44 Mem0g). The real gains are cost and latency: 1,764 vs 26,031 context tokens, and p95 total latency 1.44 s vs 17.12 s. Zep (corrected Zep score 75.14) and Letta (Mem0 couldn't have run MemGPT as described; a filesystem agent scored 74.0%) dispute its baselines. Independent and third-party tests put Mem0 near the bottom: overall 21.1 on MemoryAgentBench, and 3.23% extraction recall on HaluMem-Long.

### Cited Findings
**Write path (vendor, 28 Apr 2025)**
- **Extraction** runs on each new message pair (m_{t−1}, m_t). The prompt is: a conversation summary S, refreshed asynchronously so it adds no latency, plus the last m = 10 messages, plus the new pair. An LLM extracts candidate facts. The extraction prompt itself isn't in the paper — [Mem0 paper](https://arxiv.org/html/2504.19413)
- **Update.** For each candidate fact, Mem0 retrieves the top s = 10 semantically similar memories (dense embeddings). One LLM function call then chooses an operation:
  - **ADD:** no equivalent memory exists.
  - **UPDATE:** augments an existing memory; it replaces the old one only if the new fact carries more information (Algorithm 1).
  - **DELETE:** removes a memory that the new fact contradicts.
  - **NOOP:** the fact is already stored or irrelevant.

  gpt-4o-mini is used for every LLM step — [Mem0 paper](https://arxiv.org/html/2504.19413)
- **Mem0g.**
  - A directed labeled graph whose entity nodes carry a type, an embedding and a creation timestamp.
  - Two LLM stages: an entity extractor, then a relationship generator that produces triplets (e.g., `lives_in`, `prefers`).
  - Nodes are reused when embedding similarity exceeds a threshold t.
  - Conflict detection plus an LLM update resolver. Obsolete relations are **marked invalid, not deleted**, "to support temporal reasoning".
  - Storage is Neo4j.
  - [Mem0 paper](https://arxiv.org/html/2504.19413)

**Read path**
- Mem0 uses dense-vector top-k over facts. Mem0g has two modes: entity-centric (find query entities, then traverse their incoming and outgoing edges) and semantic-triplet (embed the query and match it against triplet encodings above a threshold) — [Mem0 paper](https://arxiv.org/html/2504.19413)

**LoCoMo results (vendor self-report; the adversarial category is excluded)**
- **Per category, J (Table 1):**

  | System | Single-hop | Multi-hop | Open-domain | Temporal |
  |---|---|---|---|---|
  | Mem0 | 67.13 ± 0.65 | 51.15 ± 0.31 | 72.93 ± 0.11 | 55.51 ± 0.34 |
  | Mem0g | 65.71 | 47.19 | 75.71 | 58.13 |
  | Zep (Mem0's run) | 61.70 | 41.35 | **76.60** | 49.31 |
  | LangMem | 62.23 | 47.92 | 71.12 | 23.43 |
  | OpenAI memory | 63.79 | 42.92 | 62.29 | 21.71 |
  | A-Mem* (re-run) | 39.79 | 18.85 | 54.05 | 49.91 |

  Mem0's F1 by category is 38.72 / 28.64 / 47.65 / 48.93. Full context is reported only as an overall number — [Mem0 paper](https://arxiv.org/html/2504.19413)
- **Overall J, context tokens per query, and total latency p50/p95 (Table 2):**

  | System | Overall J | Context tokens | Total latency p50 / p95 |
  |---|---|---|---|
  | **Full context** | **72.90 ± 0.19** | 26,031 | 9.870 / 17.117 s |
  | Mem0g | 68.44 | 3,616 | 1.091 / 2.590 s |
  | Mem0 | 66.88 | 1,764 | 0.708 / 1.440 s |
  | Zep (Mem0's run) | 65.99 | 3,911 | 1.292 / 2.926 s |
  | Best raw-chunk RAG (k=2, 256-token chunks) | 60.97 | – | – |
  | LangMem | 58.10 | 127 | search p95 59.82 s |
  | OpenAI memory | 52.90 | 4,437 | total p95 0.889 s |
  | A-Mem | 48.38 | 2,520 | – |

  Mem0's search alone takes p50 0.148 s and p95 0.200 s. The other raw-chunk RAG settings score 36.84–60.53 — [Mem0 paper](https://arxiv.org/html/2504.19413)
- **Memory footprint:** Mem0 averages ~7k tokens per conversation and Mem0g ~14k, against ~26k for the raw conversation. Mem0 says Zep exceeds 600k — [Mem0 paper](https://arxiv.org/html/2504.19413)
- **Headline claims:** +26% relative J over OpenAI (66.88 vs 52.90), 91% lower p95 latency, and >90% fewer tokens. These check out against the tables; the body says 92% for the latency — [Mem0 paper](https://arxiv.org/html/2504.19413)

**Disputes**
- **Zep (vendor, 6 May 2025).** The misconfiguration is described in §1. Zep's corrected score is 75.14% ± 0.17 J, above Mem0g's 68.44 and Mem0's 66.88.
  - Zep's criticisms of LoCoMo: conversations average ~16k–26k tokens, which fit in context; full context (~73%) beats Mem0's best; there are no knowledge-update questions; category 5 is excluded because its answers are missing; some BLIP image captions lack the needed information; some questions misattribute speakers or have several valid answers.
  - Zep prefers LongMemEval (~115k tokens).
  - [Zep rebuttal](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)
- **Letta (vendor, 12 Aug 2025).** Letta says it could not find a way to load LoCoMo into MemGPT/Letta without major refactoring, and Mem0 did not answer its requests for the modified MemGPT code. Letta's own agent, given the raw LoCoMo conversation as an attached file plus file tools on gpt-4o-mini, scored **74.0%** vs Mem0's "68.5%" for its graph variant — [Letta benchmark post](https://www.letta.com/blog/benchmarking-ai-agent-memory)

**Other teams' runs of Mem0 (scores vary by ~20 points with setup)**
- MIRIX (gpt-4.1-mini): 62.47 overall [competitor re-run] — [MIRIX paper](https://arxiv.org/html/2507.07957)
- MemOS (gpt-4o-mini) [competitor re-run] — [MemOS paper](https://arxiv.org/html/2507.03724):
  - LoCoMo 64.57 with 1,172 tokens.
  - LongMemEval 66.4 overall, but **26.8 on single-session-assistant** vs 90.0 on single-session-preference.
  - At 10 QPS: add mean 888 ms (P99 2,841) and search mean 1,089 ms (P99 4,637).
- LightMem [academic] — [LightMem paper](https://arxiv.org/html/2510.18866):
  - LoCoMo 61.69 (gpt-4o-mini).
  - LongMemEval-S 53.61 (gpt-4o-mini) and 39.51 (Qwen3-30B-A3B). Both are **below FullText** (56.80 / 54.80) and below NaiveRAG (61.00 / 60.80).
- Memory-R1 (8B open models) [academic]:
  - LoCoMo J 45.68 (LLaMA-3.1-8B) and 53.30 (Qwen-2.5-7B).
  - LongMemEval, zero-shot: J 41.20 and 46.80.
  - [Memory-R1 paper](https://arxiv.org/html/2508.19828)
- MemoryAgentBench [independent benchmark]. Mem0 scores: accurate retrieval 32.6, test-time learning 21.2, long-range understanding 20.7, selective forgetting 18.0 / 2.0, **overall 21.1**. BM25 over raw chunks scores 60.5 on accurate retrieval and 41.5 overall — [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- HaluMem [Nov 2025, MemOS-affiliated authors] — [HaluMem](https://arxiv.org/html/2511.03506):
  - **Extraction recall:** 42.91% (Medium) and **3.23% (Long)**, while target precision stays high (86.26% / 88.01%).
  - **Updates:** correct 25.50% / 1.45%; omission 74.02% / **98.51%**.
  - **QA correct:** 53.02% / 28.11%.
  - **Mem0-Graph:** recall 43.28% / 2.24%.
  - **Cost:** adding the Medium set took Mem0 2,768 minutes.

### Inferences
- Mem0 trades recall for cost. What it stores is precise (~86–88% target precision in HaluMem), but much is never stored (recall 43% on Medium, ~3% on Long). Questions whose details weren't extracted, and questions about what the assistant said (26.8 in MemOS's run), fail.
- DELETE destroys history. Mem0g's "mark invalid" and Zep's `t_invalid` keep it. HaluMem's >70% update omission for Mem0 shows the reconcile step mostly fails to find the old memory, which is a retrieval-recall problem at write time.
- On LoCoMo, conversations are short enough that full context is the ceiling. Mem0's 6-point deficit to full context in its own table is the clearest vendor-acknowledged evidence that extraction loses information.
- Two runs conflict on raw-chunk RAG vs Mem0 on LoCoMo. Mem0's run has the best RAG at 60.97 < Mem0 66.88. LightMem's run has NaiveRAG at 63.64 > Mem0 61.69. Setup choices dominate.
- **What transfers:**
  - The write path is the closest published analogue to a background "extract, then reconcile" job: a rolling summary plus the last 10 messages plus the new pair go to a small model.
  - Candidate memories (top s = 10) can come from BM25 over existing statements and subjects instead of embeddings.
  - Allow ADD / UPDATE / NOOP plus a "supersede", which sets `valid_to`, instead of DELETE.
  - At query time, replace Mem0's 0.148 s vector search with BM25. In MemoryAgentBench, BM25 scored 60.5 on accurate retrieval, above Text-Embed-3-Small (53.8) and "most embedding-based methods" (the stronger embedders' scores weren't captured).
- **What doesn't transfer:** the dense similarity used for both candidate lookup and query retrieval.
- The 90% token saving matters less for a coding agent than recall: a missed decision or caveat costs more than 1–2k extra tokens.

### Gaps
- The Mem0 extraction prompt is not published in the paper.
- I found no Mem0 reply to the Zep or Letta criticisms (I didn't search for one specifically).
- Benchmark claims for newer Mem0 versions (late 2025–2026) are not covered here.
- Whether the Mem0 paper was peer-reviewed is unconfirmed.
- The judge model in Mem0's J metric was not captured in my fetch.

## 3. A-MEM (Zettelkasten-style agentic memory): note construction, link generation, memory evolution, reported gains

### Takeaway
A-MEM (academic preprint; first posted Feb 2025, v11 on 8 Oct 2025) keeps each raw interaction inside a "note" that an LLM enriches with keywords, tags and a context description. It links each new note to neighbours an LLM approves from its top-10 embedding matches, and lets new notes rewrite their neighbours' metadata. Its own LoCoMo gains are large for 1–3B open models and modest for GPT-4o-mini, and it loses to the plain LoCoMo baseline on adversarial questions and, with GPT-4o, on single-hop. Other teams' runs score it much lower on LoCoMo (Mem0's A-Mem* 48.38 J), but one academic run on LongMemEval-S puts it above full text (62.60 vs 56.80).

### Cited Findings
**What it stores and how it writes**
- **Note** = original content, timestamp, LLM keywords, LLM tags, LLM contextual description, an embedding of all of these concatenated (all-MiniLM-L6-v2), and links — [A-MEM paper](https://arxiv.org/html/2502.12110)
- **Link generation.** The new note's embedding is compared by cosine with existing notes, and the top-k (default k = 10) become candidates. An LLM decides which links to create — [A-MEM paper](https://arxiv.org/html/2502.12110)
- **Memory evolution.** For each neighbour, an LLM decides whether to update that neighbour's context, keywords and tags, and the evolved note replaces the original. The prompt template also lists merge and prune actions — [A-MEM paper](https://arxiv.org/html/2502.12110)

**How it retrieves**
- The query is embedded and the top-k notes by cosine are returned. Notes linked to a retrieved note are also accessed, but this appears only in the Figure 2 caption and isn't formalised in §3.4. Table 8 uses k = 40–50 for GPT models in several categories — [A-MEM paper](https://arxiv.org/html/2502.12110)

**Results (self-reported, F1 / BLEU-1, A-MEM's own category labels)**
- LoCoMo baseline → A-MEM:

  | Category | GPT-4o-mini | GPT-4o |
  |---|---|---|
  | Multi-hop | 25.02/19.75 → 27.02/20.09 | 28.00/18.47 → 32.86/23.76 |
  | Temporal | 18.41/14.77 → 45.85/36.67 | 9.09/5.78 → 39.41/31.23 |
  | Open domain | 12.04/11.16 → 12.14/12.00 | 16.47/14.80 → 17.10/15.84 |
  | Single-hop | 40.36/29.05 → 44.65/37.06 | **61.56/54.19 → 48.43/42.97** |
  | Adversarial | **69.23/68.75 → 50.03/49.47** | **52.61/51.13 → 36.35/35.53** |

  Bold rows are where A-MEM is worse than the baseline — [A-MEM paper](https://arxiv.org/html/2502.12110)
- Small open models gain most. Qwen2.5-3b multi-hop F1 goes from 4.61 to 12.57, and Llama 3.2-1b from 11.25 to 19.06 — [A-MEM paper](https://arxiv.org/html/2502.12110)
- **Cost:**
  - ~1,200 tokens per memory operation vs ~16,900 for LoCoMo and MemGPT (85–93% less).
  - Under $0.0003 per operation.
  - Latency ~5.4 s per operation with GPT-4o-mini and 1.1 s with Llama 3.2 1B on one GPU.
  - [A-MEM paper](https://arxiv.org/html/2502.12110)
- **Ablation (GPT-4o-mini, F1):**

  | Variant | Multi-hop | Temporal | Single-hop |
  |---|---|---|---|
  | No links, no evolution | 9.65 | 24.55 | 13.28 |
  | Links, no evolution | 21.35 | 31.24 | 39.17 |
  | Full A-MEM | 27.02 | 45.85 | 44.65 |

  The paper credits link generation with the largest contribution — [A-MEM paper](https://arxiv.org/html/2502.12110)
- **DialSim:** A-MEM F1 3.45 vs LoCoMo 2.55 and MemGPT 1.18 — [A-MEM paper](https://arxiv.org/html/2502.12110)
- **Caveats:** no error bars or significance tests (the checklist says repeated API calls were too costly), and some inconsistent table entries. The page includes a NeurIPS checklist, but acceptance is not confirmed in the fetched text — [A-MEM paper](https://arxiv.org/html/2502.12110)

**Other teams' runs**
- Mem0's "A-Mem*" (gpt-4o-mini): F1 20.76 / 9.22 / 33.34 / 35.40 (temporal 35.40 vs the self-reported 45.85). J 39.79 / 18.85 / 54.05 / 49.91, overall 48.38 [competitor re-run] — [Mem0 paper](https://arxiv.org/html/2504.19413)
- MemoryOS's A-Mem*: average F1 26.55 with 2,712 tokens and **13.0 LLM calls** per response [competitor re-run] — [MemoryOS paper](https://arxiv.org/html/2506.06326)
- MIRIX's A-Mem row (39.79 / 18.85 / 54.05 / 49.91 / 48.38) is identical to Mem0's A-Mem* J values. It was copied, under a gpt-4o-mini backbone, into a table that is otherwise gpt-4.1-mini — [MIRIX paper](https://arxiv.org/html/2507.07957); [Mem0 paper](https://arxiv.org/html/2504.19413)
- LightMem (LongMemEval-S) [academic]: A-MEM 62.60 (gpt-4o-mini), 65.20 (Qwen3-30B-A3B), 70.60 (GLM-4.6). It beats FullText (56.80 / 54.80 / 36.71) and is the strongest non-LightMem baseline. On LoCoMo (gpt-4o-mini) it scores 64.16 — [LightMem paper](https://arxiv.org/html/2510.18866)
- Memory-R1: A-Mem J 44.76 (LLaMA-3.1-8B) and 40.78 (Qwen-2.5-7B) — [Memory-R1 paper](https://arxiv.org/html/2508.19828)

**LoCoMo category labels are not consistent across papers (data-quality finding)**
- A-MEM labels its GPT-4o-mini numbers 27.02/20.09 as *multi-hop*, 12.14/12.00 as *open domain* and 44.65/37.06 as *single-hop*. Mem0's paper reports the same numbers as *single-hop*, *multi-hop* and *open-domain* respectively; only temporal (45.85) matches. The same relabelling applies to the LoCoMo baseline row (25.02 / 12.04 / 40.36) — [A-MEM paper](https://arxiv.org/html/2502.12110); [Mem0 paper](https://arxiv.org/html/2504.19413)

### Inferences
- **Per-category LoCoMo numbers can't be compared across papers.** Only within-paper comparisons and overall scores are safe.
- A-MEM keeps the raw content, so it is a "raw + derived metadata" design. Its strongest component (links) is a form of key and neighbourhood expansion. That matches LongMemEval's finding that expanding the index with derived facts helps more than replacing the text (§7).
- **What transfers:**
  - Store records with the raw text intact, and add background-LLM keywords, tags and a one-line context as extra BM25 fields. This is lexical "key expansion", which narrows the vocabulary gap that embeddings would otherwise close.
  - Generate links in the background. Candidate neighbours can come from BM25 or Jaccard over keywords instead of MiniLM, with an LLM approving the links.
  - At query time, BM25 top-k plus a one-hop expansion along links. This is pure Python and fits in 0.5 s.
  - The ~5.4 s per operation is fine as a background job.
- Evolution overwrites the neighbours' metadata. In an append-only store it should write new versions instead.
- **What doesn't transfer:** the MiniLM embeddings, and the per-category tuning of k (40–50).

### Gaps
- The NeurIPS 2025 acceptance is not verified.
- There is no independent (non-competitor) replication on LoCoMo.
- The 1,200-token figure is per memory operation; the cost of the whole write path for a long history is not reported.

## 4. MemGPT / Letta: tiered memory (core, recall, archival), self-editing memory tools, and sleep-time compute (2025)

### Takeaway
MemGPT (UC Berkeley preprint, Oct 2023, v2 12 Feb 2024; its authors went on to build Letta) treats the context window like RAM. A small editable "working context" and a FIFO message queue stay in context. **Recall storage keeps the full raw message history** outside it, and archival storage holds vector-searched text. The LLM pages data in and out through function calls. Its DMR result (GPT-4: 32.1% → 92.5%) is measured against a recursive-summary baseline, and the benchmark is now saturated. Letta's 2025 additions are vendor work:
- Memory blocks.
- Sleep-time agents: a background agent edits the main agent's core memory. The paper reports ~5× less test-time compute at equal accuracy, up to +13% / +18% accuracy, and 2.5× lower cost per query, all on stateful math benchmarks.
- A filesystem experiment: the raw conversation in an attached file plus grep and semantic file search scored 74.0% on LoCoMo with gpt-4o-mini.

### Cited Findings
**Architecture (academic preprint, Feb 2024)**
- **Main context:** read-only system instructions, a fixed-size read/write working context for key facts and preferences, and a FIFO message queue whose first entry is a recursive summary of evicted messages.
- **External context:** recall storage (the full message database) and archival storage (text of any length, searched by vector similarity).
- [MemGPT paper](https://arxiv.org/html/2310.08560)
- **Queue manager.**
  - At a warning threshold (e.g., 70% of the window) it inserts a "memory pressure" warning so the model can save what matters.
  - At the flush threshold (e.g., 100%) it evicts a share of messages (e.g., 50%) and updates the recursive summary.
  - **Evicted messages remain in recall storage.**
  - [MemGPT paper](https://arxiv.org/html/2310.08560)
- **Control flow.** A function executor parses the model's output as function calls and returns results or errors. `request_heartbeat=true` chains another inference step immediately. Retrieval results are paginated so they don't overflow the context — [MemGPT paper](https://arxiv.org/html/2310.08560)

**Results (self-reported)**
- **DMR (Table 2)**, accuracy / ROUGE-L, base model → with MemGPT:

  | Model | Accuracy | ROUGE-L |
  |---|---|---|
  | GPT-3.5 Turbo | 38.7% → 66.9% | 0.394 → 0.629 |
  | GPT-4 | 32.1% → 92.5% | 0.296 → 0.814 |
  | GPT-4 Turbo | 35.3% → 93.4% | 0.359 → 0.827 |

  [MemGPT paper](https://arxiv.org/html/2310.08560). Zep labels the 35.3% GPT-4 Turbo baseline "Recursive Summarization" and adds a full-conversation baseline at 94.4% — [Zep paper](https://arxiv.org/html/2501.13956)
- **Conversation openers (SIM-1 / SIM-3 / SIM-H):** GPT-4 0.868 / 0.843 / 0.773 vs human 0.800 / 0.800 / 1.000 — [MemGPT paper](https://arxiv.org/html/2310.08560)
- **Nested key-value retrieval** (140 UUID pairs, ~8k tokens): GPT-3.5 falls to 0% at one nesting level, and GPT-4 and GPT-4 Turbo reach 0% by three levels, while MemGPT with GPT-4 stays consistent. **Document QA:** MemGPT's accuracy stays flat as documents grow and degrades with GPT-3.5 because of weak function calling — [MemGPT paper](https://arxiv.org/html/2310.08560)
- **Cost on LoCoMo** [competitor re-runs]. MemoryOS reports MemGPT at 16,977 tokens and 4.3 LLM calls per response, with average F1 29.13 — [MemoryOS paper](https://arxiv.org/html/2506.06326). A-MEM cites ~16,900 tokens per operation for LoCoMo and MemGPT — [A-MEM paper](https://arxiv.org/html/2502.12110)
- **MemoryAgentBench** [independent benchmark]. MemGPT scores: accurate retrieval 34.3, test-time learning 40.8, long-range understanding 22.4, selective forgetting 28.0 / 3.0, overall 28.3. BM25 scores 41.5 overall and GPT-4o-mini long context 42.2 — [MemoryAgentBench](https://arxiv.org/html/2507.05257)

**Letta (vendor, 2025)**
- **Memory model (7 Jul 2025).**
  - **Core memory:** editable in-context blocks, each with a label, description, value and character limit. They are pinned to the context and can be shared across agents.
  - **Recall memory:** the full conversation history, saved to disk automatically and searchable.
  - **Archival memory:** processed, indexed knowledge in external storage ("vector or graph database").
  - **Overflow:** a portion of messages ("e.g., 70%") is evicted and recursively summarised with earlier summaries.
  - [Letta agent-memory post](https://www.letta.com/blog/agent-memory)
- The docs say blocks are "pieces of context (strings) that are editable by agents via memory tools", that blocks can be attached to several agents, and that "all messages are stored", so old messages stay retrievable after compaction through the API and retrieval tools — [Letta memory docs](https://docs.letta.com/guides/agents/memory)
- **Sleep-time compute, paper** (arXiv 17 Apr 2025; co-authors include MemGPT's Charles Packer and Sarah Wooders):
  - On Stateful GSM-Symbolic and Stateful AIME, it needs ~5× less test-time compute for the same accuracy.
  - Scaling sleep-time compute raises accuracy by up to 13% and 18% respectively.
  - On Multi-Query GSM-Symbolic, amortising across related queries lowers average cost per query by 2.5×.
  - Effectiveness correlates with how predictable the user's query is.
  - [Sleep-time paper](https://arxiv.org/abs/2504.13171)
- **Sleep-time compute, implementation** (21 Apr 2025).
  - Creating a sleep-time agent creates two agents. The **primary agent has no tools to edit core memory**; the sleep-time agent has them and manages the primary's in-context blocks asynchronously.
  - The two can use different models (fast primary, slower and larger sleep-time agent), and the run frequency is configurable at a token cost.
  - The post shows benefits only on math benchmarks and expects, without demonstrating, benefits for conversational agents.
  - [Letta sleep-time post](https://www.letta.com/blog/sleep-time-compute)
- **Filesystem experiment (12 Aug 2025).**
  - The LoCoMo history was put into a file attached to the agent. "Letta automatically parses and embeds files for semantic search."
  - Tools: `grep`, `search_files`, `open`, `close`, `answer_question`. Tool rules forced the agent to start with `search_files` and keep searching until it called `answer_question`.
  - On gpt-4o-mini it scored **74.0%** vs Mem0's reported 68.5%.
  - Letta concludes that whether an agent remembers depends mostly on whether it knows when and how to use retrieval tools, and that familiar filesystem tools beat complex structures such as knowledge graphs.
  - [Letta benchmark post](https://www.letta.com/blog/benchmarking-ai-agent-memory)

### Inferences
- MemGPT and Letta are the clearest "keep everything raw, curate a small always-loaded summary" design. Recall storage is lossless, while core memory is curated by the agent.
- The filesystem result is the strongest vendor evidence that raw text plus agent-driven search can match extraction pipelines on LoCoMo. Three caveats:
  1. It is a vendor self-report.
  2. It is not embedding-free, because `search_files` is semantic search over embedded files.
  3. LoCoMo fits in context, so 74.0 is roughly the full-context ceiling (72.90 in Mem0's run).
- The sleep-time evidence is math-only. The predictability finding suggests precomputing pays off when future questions are predictable. For a coding agent, likely questions include "why did we reject X", "what depends on Y" and "current status of Z".
- **What transfers:**
  - Claude Code already has the tiers: CLAUDE.md and always-loaded memory files are core memory, its local JSONL transcripts are recall storage, and topic/record files are archival storage.
  - Self-editing becomes Claude editing files.
  - The sleep-time split (the primary can't edit core memory; a background agent rewrites it) maps directly to a background small-model job that rewrites a size-capped always-loaded summary, while hooks deny the main agent direct edits to script-owned files.
  - Grep over raw transcripts is embedding-free.
- **What doesn't transfer:** archival vector search. Letta's "the agent decides how to search" approach costs several tool calls per answer by the main model (fine for accuracy, but not a <0.5 s per-message injection).

### Gaps
- I could not verify the exact names of Letta's memory tools from fetched pages. The legacy docs pages I fetched don't list them. From prior knowledge, *unverified*: `core_memory_append`/`core_memory_replace`, `memory_insert`/`memory_replace`/`memory_rethink`, `archival_memory_insert`/`archival_memory_search`, `conversation_search`.
- I found no Letta numbers on LongMemEval, and no Letta Leaderboard numbers were fetched.
- The sleep-time paper's SWE case study was not detailed in the abstract.
- MemGPT's peer-review status is not confirmed.

## 5. MemoryOS, MIRIX, LightMem, MemOS, Memory-R1 and other notable 2025–2026 systems: key ideas and numbers

### Takeaway
The 2025–2026 systems converge on four ideas:
- Layered stores: short-, mid- and long-term (MemoryOS, LightMem), or typed stores (MIRIX's six types).
- **Offline or "sleep-time" consolidation** (LightMem, as in Letta).
- Learned update operations (Memory-R1's RL-trained ADD/UPDATE/DELETE/NOOP).
- Lifecycle and provenance metadata (MemOS).

Their headline numbers are self-reported, and they drop sharply when competitors re-run them. MIRIX reports 85.38 on LoCoMo, while MemOS's run gives 64.33. MemoryOS falls below FullText in LightMem's run. Raw full text still beats every one of them in some setting.

### Cited Findings
**MemoryOS** (BUPT + Tencent AI Lab; arXiv 30 May 2025; academic/industry preprint)
- **Short-term memory:** a queue of dialogue "pages" (query, response, timestamp) with a chain meta-summary; queue length 7. **Mid-term memory:** topic segments; a page joins a segment if its similarity exceeds θ = 0.6. "Segment capacity" is 200; the fetched text doesn't make clear whether that means 200 segments or 200 pages per segment. **Long-term personal memory:** a user persona (static attributes, a user knowledge base, and 90-dimension user traits) and agent traits. The user knowledge base and agent traits hold ≤100 entries each, FIFO — [MemoryOS paper](https://arxiv.org/html/2506.06326)
- **Update rules.**
  - Short- to mid-term transfer is FIFO.
  - **Heat = N_visit + L_interaction + R_recency** (all weights 1), with R_recency = exp(−Δt/μ) and μ = 1e7 s.
  - The lowest-heat segments are evicted.
  - Segments with heat > τ = 5 are promoted into the persona and knowledge base, and L_interaction is then reset.
  - [MemoryOS paper](https://arxiv.org/html/2506.06326)
- **Retrieval.** All short-term pages are returned. Mid-term segments are scored by **cosine + Jaccard keyword similarity**, and the top 5 are kept; then the top-k pages inside them (k = 10 on LoCoMo). Visit counts and recency are updated after retrieval. The long-term store contributes the top 10 knowledge-base entries and the top 10 agent traits — [MemoryOS paper](https://arxiv.org/html/2506.06326)
- **Results (self-reported, GPT-4o-mini).**
  - LoCoMo F1 / BLEU-1: single-hop 35.27 / 25.22, multi-hop 41.15 / 30.76, temporal 20.02 / 16.52, open-domain 48.62 / 42.99.
  - The abstract claims +49.11% F1 and +46.18% BLEU-1 on average over baselines.
  - Cost per response: 3,874 tokens and 4.9 LLM calls, with average F1 36.23 (MemGPT: 16,977 tokens, 4.3 calls, 29.13).
  - On GVD: accuracy 93.3 vs A-Mem 90.4.
  - [MemoryOS paper](https://arxiv.org/html/2506.06326)
- **Others' runs.** On LongMemEval-S, MemoryOS scores 44.80 (gpt-4o-mini), **below FullText at 56.80**, and 49.60 on Qwen — [LightMem paper](https://arxiv.org/html/2510.18866). On LoCoMo it gets J 48.20 (LLaMA-3.1-8B) and 51.26 (Qwen-2.5-7B) — [Memory-R1 paper](https://arxiv.org/html/2508.19828)

**MIRIX** (arXiv 10 Jul 2025; self-reported by its authors)
- **Six memory types.**
  - **Core:** persona and human blocks, rewritten when more than 90% full.
  - **Episodic:** event_type, summary, details, actor, timestamp.
  - **Semantic:** name, summary, details, source.
  - **Procedural:** entry_type (workflow, guide or script), description, steps.
  - **Resource:** title, summary, resource_type, content.
  - **Knowledge Vault:** verbatim sensitive values with sensitivity levels and access control.
  - [MIRIX paper](https://arxiv.org/html/2507.07957)
- A Meta Memory Manager routes input to six per-type managers that update in parallel, and a Chat Agent handles dialogue. **"Active Retrieval"** first generates the current topic from the input, then retrieves the top 10 per memory type, tagged by source. Retrieval modes are `embedding_match`, `bm25_match` and `string_match` — [MIRIX paper](https://arxiv.org/html/2507.07957)
- **ScreenshotVQA** (gemini-2.5-flash backbone):

  | System | Accuracy | Storage |
  |---|---|---|
  | MIRIX | 0.5950 | 15.89 MB |
  | SigLIP@50 RAG | 0.4410 | 15.07 GB |
  | Gemini long context | 0.1166 | 236.70 MB |

  That is ~35% higher accuracy than RAG with 99.9% less storage — [MIRIX paper](https://arxiv.org/html/2507.07957)
- **LoCoMo** (gpt-4.1-mini backbone, GPT-4.1 judge):

  | System | Single-hop | Multi-hop | Open-domain | Temporal | Overall |
  |---|---|---|---|---|---|
  | MIRIX | 85.11 | **83.70** | 65.62 | 88.39 | 85.38 |
  | **Full context** | **88.53** | 77.70 | 71.88 | **92.70** | **87.52** |
  | Zep | 79.43 | 69.16 | **73.96** | 83.33 | 79.09 |
  | LangMem | 74.47 | 61.06 | 67.71 | 86.92 | 78.05 |
  | Mem0 | 62.41 | 57.32 | 44.79 | 66.47 | 62.47 |
  | RAG-500 | 37.94 | 37.69 | 48.96 | 61.83 | 51.62 |
  | A-Mem* (gpt-4o-mini, copied from Mem0's paper) | 39.79 | 18.85 | 54.05 | 49.91 | 48.38 |

  MIRIX's claim to beat "the best existing method" excludes full context — [MIRIX paper](https://arxiv.org/html/2507.07957)
- **Others' runs.** MemOS (gpt-4o-mini) gets MIRIX LoCoMo 64.33 and LongMemEval 43.49 — [MemOS paper](https://arxiv.org/html/2507.03724). MemoryAgentBench gets MIRIX overall 26.2 (gpt-4o-mini) and 37.7 (gpt-4.1-mini), with accurate retrieval 47.5 and 63.0 — [MemoryAgentBench](https://arxiv.org/html/2507.05257)

**LightMem** (Zhejiang University et al.; arXiv Oct 2025, v4 28 Feb 2026; academic preprint)
- **Stage 1, sensory memory:** pre-compression with LLMLingua-2 (a BERT token classifier, retention ratio 0.4–0.8) and topic segmentation that intersects attention-based and similarity-based boundaries. The sensory buffer is 512 tokens. **Stage 2, topic-aware short-term memory:** an LLM summarises a topic group when the buffer reaches a token threshold. **Stage 3, long-term memory with "sleep-time" update:** at test time new entries are only inserted with timestamps ("soft update", no overwrite or delete). Offline, each entry gets a queue of its top-k similar later entries, and the queues are processed in parallel with add / delete / update / merge — [LightMem paper](https://arxiv.org/html/2510.18866)
- **Stores** topic labels, summaries, the (compressed) user and model turns, summary embeddings (all-MiniLM-L6-v2) and timestamps. Retrieval is cosine — [LightMem paper](https://arxiv.org/html/2510.18866)
- **LongMemEval-S accuracy:**

  | System | gpt-4o-mini | Qwen3-30B-A3B | GLM-4.6 |
  |---|---|---|---|
  | **LightMem** | **68.64** | **70.20** | **73.20** |
  | A-MEM | 62.60 | 65.20 | 70.60 |
  | **NaiveRAG** | 61.00 | 60.80 | **73.20** |
  | FullText | 56.80 | 54.80 | 36.71 |
  | Mem0 | 53.61 | 39.51 | – |
  | MemoryOS | 44.80 | 49.60 | – |
  | LangMem | 37.20 | 50.80 | 49.20 |

  NaiveRAG ties LightMem on GLM-4.6. The text's claimed gains (2.09–6.40 points) don't exactly match the table — [LightMem paper](https://arxiv.org/html/2510.18866)
- **Per type (gpt-4o-mini).** LightMem scores **32.14 on single-session-assistant vs NaiveRAG's 98.21**, and 31.25 on Qwen. It is best on temporal (67.18), multi-session (71.74) and knowledge-update (83.12) — [LightMem paper](https://arxiv.org/html/2510.18866)
- **Efficiency on LongMemEval:**
  - Total tokens up to 38× fewer (GPT) and 21.8× (Qwen) with offline cost included; online only, 105.9× and 117.1×.
  - API calls up to 30× and 17.1× fewer; online only, 159.4× and 309.9×.
  - Runtime up to 12.4× and 6.3× faster.
  - [LightMem paper](https://arxiv.org/html/2510.18866)
- **LoCoMo.** With gpt-4o-mini, LightMem scores 72.99 vs FullText 71.83, A-MEM 64.16, NaiveRAG 63.64 and Mem0 61.69. With Qwen3, **FullText (74.87) beats LightMem (72.60)** — [LightMem paper](https://arxiv.org/html/2510.18866)

**MemOS** (MemTensor (Shanghai) plus universities; arXiv Jul 2025, v4 3 Dec 2025; **vendor**)
- **Three memory types:**
  - Plaintext: editable passages, graphs and templates.
  - Activation: KV cache and hidden states.
  - Parameter: weights, LoRA and adapters.

  A scheduler moves knowledge between them, e.g., turning frequently used plaintext into KV cache — [MemOS paper](https://arxiv.org/html/2507.03724)
- **MemCube metadata.**
  - Descriptive: timestamp, origin signature, semantic type, contextual fingerprint.
  - Governance: access control, lifespan (TTL or decay), priority, sensitivity tags, logs.
  - Usage: access frequency and recency, plus a **version chain** for conflict resolution and rollback.

  A Provenance API tags each memory with a provenance ID. Lifecycle states are Generated / Activated / Merged / Archived / (Expired), and critical memories can be "Frozen". Plaintext is organised as a hierarchical graph of task, concept and fact paths. Retrieval combines structured filters (tags, time spans, access policy) with embedding similarity — [MemOS paper](https://arxiv.org/html/2507.03724)
- **LoCoMo (gpt-4o-mini, LLM judge):**

  | System | Overall | Tokens | Note |
  |---|---|---|---|
  | MemOS | 75.80 | 1,589 | |
  | Memobase | 72.01 | – | leads temporal: 81.20 vs MemOS 75.18 |
  | Mem0 | 64.57 | – | |
  | MIRIX | 64.33 | – | |
  | Zep | 59.22 | – | |
  | MemU | 56.55 | – | |
  | Supermemory | 55.34 | – | |

  No full-context row appears — [MemOS paper](https://arxiv.org/html/2507.03724)
- **LongMemEval:**

  | System | Overall | Single-session-assistant |
  |---|---|---|
  | MemOS | 77.8 | 67.9 |
  | Memobase | 72.4 | 23.2 |
  | Mem0 | 66.4 | 26.8 |
  | Zep (copied from Zep's paper) | 63.8 | **75.0** |
  | Supermemory | 58.4 | 58.9 |
  | MIRIX | 43.49 | – |
  | MemU | 38.4 | 19.6 |

  On single-session-assistant, Zep's 75.0 is higher than MemOS's 67.9. MemOS is also not first on knowledge-update (Memobase 89.7) — [MemOS paper](https://arxiv.org/html/2507.03724)
- **Latency at 10 QPS:** MemOS search mean 440.5 ms (P99 777.1) vs Mem0 1,089 ms and Zep 571.7 ms. **KV-cache "activation memory":** time-to-first-token cut by 18.6–94.2% (91.4% for Qwen2.5-72B with a long context and short query), assuming memories are pre-cached on the GPU — [MemOS paper](https://arxiv.org/html/2507.03724)

**Memory-R1** (arXiv Aug 2025, v5 14 Jan 2026; academic preprint)
- **Memory Manager.** It picks ADD / UPDATE / DELETE / NOOP and writes the new content. It is trained with PPO or GRPO, and its reward is the exact-match score of a frozen answer agent's answer. **Answer Agent:** it retrieves 60 candidates by similarity, then "memory distillation" keeps the relevant ones. It is trained with exact match, because an LLM-judge reward produced verbose answers. Training uses **152 LoCoMo QA pairs** (81 validation, 1,307 test, adversarial excluded). Backbones: LLaMA-3.1-8B and Qwen-2.5 3B / 7B / 14B — [Memory-R1 paper](https://arxiv.org/html/2508.19828)
- **LoCoMo, F1 / BLEU-1 / J:**

  | Backbone | Memory-R1 (GRPO) | Mem0 | MemoryOS | Memory-SFT |
  |---|---|---|---|---|
  | LLaMA-3.1-8B | **45.02 / 37.51 / 62.74** | 30.41 / 22.22 / 45.68 | 35.04 / 27.99 / 48.20 | 58.76 J |
  | Qwen-2.5-7B | 43.14 / 36.44 / 61.51 | 30.61 / 23.55 / 53.30 | – | 61.13 J |

  On LLaMA, Memory-R1 is +48% / +69% / +37% relative over Mem0 (computed from Table 1; the paper's text doesn't state these figures). The introduction attributes its 28% / 34% / 30% gains to Mem0, but they are actually over MemoryOS — [Memory-R1 paper](https://arxiv.org/html/2508.19828)
- **Zero-shot LongMemEval:** LLaMA GRPO 45.20 / 39.30 / 55.40 vs Mem0 31.41 / 21.69 / 41.20. **Ablations (J):** removing RL from the memory manager drops 62.7 → 52.9, and removing distillation drops 62.7 → 60.1 — [Memory-R1 paper](https://arxiv.org/html/2508.19828)

**Other systems that appear only inside other papers' tables**
- **Memobase, MemU, Supermemory:** numbers above come from MemOS's vendor tables. **HaluMem extraction recall**, Medium / Long: Supermemory 41.53% / 53.02%, Memobase 14.55% / 6.18%, MemOS 74.07% / 81.90% — [HaluMem](https://arxiv.org/html/2511.03506)
- **Cognee:** overall 20.6 and accurate retrieval 28.3. **HippoRAG-v2:** accurate retrieval 65.1 (the best non-long-context system) and overall 41.6 — [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- **HaluMem's authors** include Zhiyu Li and Feiyu Xiong — [HaluMem abstract](https://arxiv.org/abs/2511.03506) — who are the first and last authors of the MemOS paper — [MemOS paper](https://arxiv.org/html/2507.03724). MemOS is the top system in HaluMem.

### Inferences
- Re-runs by others are consistently far below self-reports:
  - MIRIX: 85.38 self vs 64.33 by MemOS, though the backbones differ.
  - MemoryOS: below FullText in LightMem's run.
  - Mem0: from 39.51 to 66.4 depending on who runs it and with which model.

  Treat every cross-system ranking as configuration-dependent.
- HaluMem is effectively vendor-affiliated (MemTensor authors, and MemOS wins), so its system ranking needs independent confirmation. Its per-stage method (extraction recall → update omission → QA) is still useful as a way to evaluate.
- The consistent single-session-assistant collapse is the most robust cross-paper pattern: Mem0 26.8, Memobase 23.2, MemU 19.6, LightMem 32.14, against NaiveRAG 98.21 and full context 81.8–94.6. Compression and fact extraction drop what the assistant said.
- **What transfers:**
  - MemoryOS's heat score (visit count + interaction length + exponential recency) and its Jaccard keyword similarity are pure arithmetic. Two-stage retrieval (pick topics or segments, then turns inside them) works with BM25 in place of cosine.
  - MIRIX's typed stores map to separate files. Procedural memory (workflows, steps) is directly relevant to coding agents. `bm25_match` and `string_match` are already embedding-free.
  - LightMem's "soft update online, consolidate offline" is append-only writes plus a background consolidation job.
  - MemOS's metadata fields (provenance ID, version chain, TTL, access frequency/recency, lifecycle state) are plain JSON fields.
  - Memory-R1's "retrieve wide (60), let the reader filter" can be done by the main model, at a context cost.
- **What doesn't transfer:**
  - MemoryOS: the cosine half of segment scoring.
  - MIRIX: Active Retrieval's per-query topic-generation LLM call (too slow for 0.5 s unless replaced by keyword extraction) and its embedding mode.
  - LightMem: LLMLingua-2 compression (a BERT model) and MiniLM embeddings.
  - MemOS: activation and parameter memory, which need model internals and are impossible with Claude.
  - Memory-R1: RL fine-tuning. Its ablation still shows update quality is worth ~10 J points, which argues for investing in the background update judge.

### Gaps
- I didn't fetch primary sources for Memobase, MemU, Supermemory, Cognee or LangMem; their numbers above come only from other papers.
- Late-2025 and 2026 vendor claims on LongMemEval and LoCoMo (e.g., Supermemory, Hindsight, EverMemOS, Emergence AI) and newer designs such as "General Agentic Memory" were not covered.
- Venues for MemoryOS, LightMem and Memory-R1 are not confirmed in the fetched text.
- MemOS's backbone judge model was not named in the excerpt.

## 6. Generative Agents (Park et al., 2023): recency, importance and relevance scoring, and reflection; what later work kept or dropped

### Takeaway
Generative Agents (UIST '23, **peer-reviewed**) stores every observation as a natural-language record with creation and last-access times. It retrieves by an equal-weight sum of min-max-normalised recency (0.995 decay per game hour since last access), LLM-rated importance (1–10) and embedding relevance. It periodically writes cited "reflections" when accumulated importance exceeds 150. The ablations show memory, planning and reflection each add believability: TrueSkill 29.89 full vs 21.21 with none. Later systems kept relevance everywhere, mostly dropped the explicit importance score, turned recency into heat or validity intervals, and moved reflection into background consolidation.

### Cited Findings
- **Memory stream.** Each record has a natural-language description, a creation timestamp and a most-recent-access timestamp. Observations include the agent's own actions and those of other agents — [Generative Agents](https://arxiv.org/html/2304.03442)
- **Score = α_rec·recency + α_imp·importance + α_rel·relevance, all α = 1**, each term min-max normalised to [0, 1].
  - **Recency:** exponential decay over sandbox game hours *since the memory was last retrieved*, factor 0.995.
  - **Importance:** an integer from 1 to 10 rated by the LLM at creation ("1 is purely mundane…"; e.g., 2 for cleaning the room, 8 for asking a crush out).
  - **Relevance:** embedding cosine similarity to the query.
  - The top-ranked memories that fit in the context are included.
  - [Generative Agents](https://arxiv.org/html/2304.03442)
- **Reflection.**
  - Triggered when the importance of recent events sums past 150, about two or three times per simulated day.
  - The 100 most recent records go to the LLM, which asks the 3 most salient questions. Each question is used as a retrieval query, and the model writes 5 insights **with citations** to the records ("insight (because of 1, 5, 3)").
  - Reflections can cite other reflections (a reflection tree).
  - [Generative Agents](https://arxiv.org/html/2304.03442)
- **Evaluation** (100 participants, TrueSkill μ / σ):

  | Condition | μ | σ |
  |---|---|---|
  | Full architecture | 29.89 | 0.72 |
  | No reflection | 26.88 | 0.69 |
  | No reflection or planning | 25.64 | 0.68 |
  | Human crowdworkers | 22.95 | 0.69 |
  | No memory, planning or reflection | 21.21 | 0.70 |

  d = 8.16 (prior-work condition vs full); Kruskal-Wallis H(4) = 150.29, p < 0.001 — [Generative Agents](https://arxiv.org/html/2304.03442)
- **Failure modes.** Retrieval failures (an agent failed to recall the election it had heard about, or recalled a party only partially) and embellishments (an announcement that never happened). In the end-to-end run, 1.3% (6 of 453) of responses about other agents were hallucinated — [Generative Agents](https://arxiv.org/html/2304.03442)
- arXiv v2 is dated 6 Aug 2023, and UIST '23 ran 29 Oct – 1 Nov 2023 in San Francisco — [Generative Agents](https://arxiv.org/html/2304.03442)

**What later systems have in place of each component** (descriptions cited in §1–§5)
- **Relevance by embedding:** Mem0's top-s similar memories, A-MEM's cosine top-k, Zep's cosine search (plus BM25), MemoryOS's cosine + Jaccard, LightMem's cosine, and MIRIX's `embedding_match` (plus BM25 and string match) — [Mem0](https://arxiv.org/html/2504.19413); [A-MEM](https://arxiv.org/html/2502.12110); [Zep](https://arxiv.org/html/2501.13956); [MemoryOS](https://arxiv.org/html/2506.06326); [LightMem](https://arxiv.org/html/2510.18866); [MIRIX](https://arxiv.org/html/2507.07957)
- **Recency and access tracking:**
  - MemoryOS: R_recency = exp(−Δt/μ), plus visit counts updated after retrieval — [MemoryOS](https://arxiv.org/html/2506.06326)
  - MemOS: access frequency and recency, plus lifespan (TTL or decay) — [MemOS](https://arxiv.org/html/2507.03724)
  - Zep uses explicit validity intervals and an episode-mentions reranker instead of decay — [Zep](https://arxiv.org/html/2501.13956)
- **Importance:** MemOS has a "priority level" field — [MemOS](https://arxiv.org/html/2507.03724). MemoryOS uses interaction length and visit count instead — [MemoryOS](https://arxiv.org/html/2506.06326)
- **Reflection-like consolidation:** A-MEM's memory evolution, Zep's community summaries, Letta's sleep-time agents, LightMem's offline update, and MemoryOS's promotion to the persona — [A-MEM](https://arxiv.org/html/2502.12110); [Zep](https://arxiv.org/html/2501.13956); [Letta](https://www.letta.com/blog/sleep-time-compute); [LightMem](https://arxiv.org/html/2510.18866); [MemoryOS](https://arxiv.org/html/2506.06326)

### Inferences
- **Kept:** relevance retrieval (by every system) and periodic higher-level synthesis (reflection, renamed evolution, consolidation or sleep-time).
- **Dropped:** the per-memory LLM importance score. None of the Mem0, A-MEM or Zep pipelines as described computes one. Recency decay is mostly replaced by validity intervals (Zep), heat (MemoryOS) or simple timestamps (LightMem). Reflection's citations survive as provenance: Zep's episode → entity edges (episode-to-fact traceability is mentioned but not evaluated) and MemOS's provenance IDs.
- Half-lives (computed): Generative Agents' 0.995 per game hour halves after ~138 game hours; MemoryOS's μ = 1e7 s halves after ~80 days.
- **What transfers:**
  - The whole scoring formula is arithmetic once relevance becomes normalised BM25.
  - Importance can be assigned by a background small model at write time, which fits the "small-model calls only in background" rule.
  - Recency-since-last-access needs an append-only access log written by the retrieval hook.
  - Reflection with citations is a natural background job that writes summary records pointing at source records and lines.
- **What doesn't transfer:** embedding relevance.

### Gaps
- No later paper ablates the importance score directly.
- I didn't find work testing Generative Agents' retrieval formula on factual-QA memory benchmarks.

## 7. Across systems: who keeps the raw conversation, and is there evidence that extraction alone loses details?

### Takeaway
Yes. The evidence that extraction-only memory loses details is consistent, and much of it comes from the vendors' own tables:
- On LoCoMo, where a conversation fits in the window, full context beats Mem0 and Mem0g (72.90 vs 66.88 and 68.44), MIRIX (87.52 vs 85.38) and, with Qwen3, LightMem (74.87 vs 72.60).
- Extraction and compression systems collapse on "what did the assistant say" questions (Mem0 26.8, Memobase 23.2, LightMem 32.14, vs NaiveRAG 98.21).
- HaluMem (whose authors overlap with MemOS) measures extraction recall below 60% for every system except MemOS, and 3.23% for Mem0 on long histories.
- An independent benchmark finds plain BM25 over raw chunks beats Mem0, Zep and Cognee on accurate retrieval (60.5 vs 32.6, 37.5 and 28.3).

Extraction helps in three cases:
- When the history is too long to read well: LongMemEval_S (115k tokens), where Zep gains +8.4 / +11.0 points.
- For aggregation across sessions, where facts help multi-session reasoning.
- **Most of all as index keys over raw values.** In LongMemEval, value = raw round and key = raw + extracted facts gives +9.4% recall and +5.4% accuracy, while replacing the value with facts or summaries hurts.

### Cited Findings
**Which systems keep raw text, and what they return at query time**

| System (date) | Raw turns kept? | Derived memory | Returned at query time | Source |
|---|---|---|---|---|
| Zep (Jan 2025) | Yes: episode subgraph, "non-lossy" | Entity and fact graph with bi-temporal edges; community summaries | Facts with validity dates, entity summaries, community summaries (episode traversal not evaluated) | [Zep](https://arxiv.org/html/2501.13956) |
| Mem0 / Mem0g (Apr 2025) | No (the summary is used only for extraction) | Facts; Mem0g adds triplets | Top-k facts or triplets | [Mem0](https://arxiv.org/html/2504.19413) |
| A-MEM (Feb 2025) | Yes: "original content" in each note | Keywords, tags, context, links | Top-k notes plus linked notes | [A-MEM](https://arxiv.org/html/2502.12110) |
| MemGPT / Letta (2023–2025) | Yes: recall storage keeps all messages | Core memory blocks; archival passages; recursive summary | Whatever the agent chooses to search | [MemGPT](https://arxiv.org/html/2310.08560); [Letta](https://www.letta.com/blog/agent-memory) |
| Generative Agents (2023) | Observations (natural-language events) | Reflections with citations | Top records by score | [GA](https://arxiv.org/html/2304.03442) |
| MemoryOS (May 2025) | Dialogue pages in short- and mid-term memory until evicted by heat | Persona, user knowledge base, traits | Pages plus long-term entries | [MemoryOS](https://arxiv.org/html/2506.06326) |
| MIRIX (Jul 2025) | Not as transcripts; episodic summary and details; verbatim vault values | Six typed stores | Top 10 per type | [MIRIX](https://arxiv.org/html/2507.07957) |
| LightMem (Oct 2025) | Compressed turns (LLMLingua-2) | Topic summaries | Cosine over summary embeddings | [LightMem](https://arxiv.org/html/2510.18866) |
| MemOS (Jul 2025) | Not stated in the excerpt | Plaintext graph; KV and LoRA memory | Hybrid structured and semantic | [MemOS](https://arxiv.org/html/2507.03724) |
| Memory-R1 (Aug 2025) | No: a Mem0-style fact bank | Facts | 60 candidates, then distillation | [Memory-R1](https://arxiv.org/html/2508.19828) |

**Evidence that extraction or compression loses details**
1. Mem0's own LoCoMo table: full context 72.90 J vs Mem0g 68.44 and Mem0 66.88 [vendor self-report, Apr 2025] — [Mem0 paper](https://arxiv.org/html/2504.19413)
2. MIRIX's own table: full context 87.52 vs MIRIX 85.38 overall. Full context also wins single-hop (88.53 vs 85.11), open-domain (71.88 vs 65.62) and temporal (92.70 vs 88.39), while MIRIX wins multi-hop (83.70 vs 77.70) [self-report, Jul 2025] — [MIRIX paper](https://arxiv.org/html/2507.07957)
3. LightMem: FullText 74.87 > LightMem 72.60 on LoCoMo (Qwen3). On LongMemEval-S, FullText beats LangMem, MemoryOS and Mem0 on both backbones. NaiveRAG over raw turns ties LightMem on GLM-4.6 (73.20) and scores **98.21 vs LightMem's 32.14** on single-session-assistant [academic, Oct 2025 / Feb 2026] — [LightMem paper](https://arxiv.org/html/2510.18866)
4. Zep loses to full context on single-session-assistant (81.8 → 75.0 and 94.6 → 80.4) and, with gpt-4o-mini, on knowledge-update (76.9 → 74.4) [vendor, Jan 2025] — [Zep paper](https://arxiv.org/html/2501.13956)
5. MemOS's LongMemEval table, single-session-assistant: Mem0 26.8, Memobase 23.2, MemU 19.6, against 90.0, 80.1 and 76.7 on single-session-preference [vendor competitor re-run] — [MemOS paper](https://arxiv.org/html/2507.03724)
6. **LongMemEval** (academic; first posted Oct 2024, v2 4 Mar 2025). This is the most controlled evidence. All of it is on LongMemEval_M (~1.5M tokens, 500 sessions) with a Stella V5 dense retriever.
   - "Replacing sessions or rounds with summaries or extracted facts generally hurts QA because of information loss", **except multi-session reasoning**, where facts help consistently.
   - Rounds beat sessions with GPT-4o as the reader.
   - Key design (Table 3):

     | Value | Key | R@5 | QA top-5 / top-10 (GPT-4o) |
     |---|---|---|---|
     | Round | Raw only | 0.582 | 0.615 / 0.670 |
     | Round | Fact only | 0.530 | 0.588 / 0.664 |
     | Round | **Raw + fact** | **0.644** | **0.657 / 0.720** |
     | Session | Raw only | 0.706 | 0.670 / 0.676 |
     | Session | Raw + fact | 0.732 | 0.714 / 0.700 |

   - The average gain from fact-augmented keys is +9.4% recall@k and +5.4% accuracy. Keys made only of condensed forms (summary, fact, keyphrase) don't improve recall, and keyphrase keys were worst.
   - [LongMemEval](https://arxiv.org/html/2410.10813)
7. **LoCoMo original** (academic, 27 Feb 2024; gpt-3.5-turbo-16k reader). Session summaries reach high recall (90.7 at top-10) but don't improve F1 (best 32.5), which the authors attribute to information lost in summarising. However, observations (extracted assertions) give the best F1 at top-5 (41.4 vs 31.7 for raw dialog) despite lower recall@5 (49.6 vs 58.8), "better signal-to-noise" — [LoCoMo paper](https://arxiv.org/html/2402.17753)
8. **MemoryAgentBench** [independent benchmark, UCSD, first posted Jul 2025].
   - Accurate retrieval: BM25 60.5, HippoRAG-v2 65.1, Text-Embed-3-Small 53.8, GPT-4o-mini long context 49.2. Against these, MIRIX scores 47.5, Zep 37.5, MemGPT 34.3, Mem0 32.6 and Cognee 28.3. The paper calls BM25 a strong accurate-retrieval baseline, "outperforming most embedding-based methods", but weak on long-range understanding and selective forgetting. The accurate-retrieval tasks are single- and multi-hop document QA, LongMemEval (S*) and EventQA.
   - Long context is best on test-time learning and long-range understanding. The paper attributes the shortfall of RAG and commercial memory agents to "retrieving only partial information".
   - On multi-hop selective forgetting, every method scores ≤28%.
   - Smaller chunks help accurate retrieval, while larger chunks help long-range understanding.
   - [MemoryAgentBench](https://arxiv.org/html/2507.05257)
9. **HaluMem** [Nov 2025; MemOS-affiliated authors].
   - Extraction recall is below 60% for every system except MemOS: Mem0 42.91% → 3.23% from Medium to Long, Mem0-Graph 43.28% → 2.24%.
   - Most systems omit over 50% of updates, which the authors attribute mainly to missed extraction of the earlier memory.
   - QA correctness tracks extraction recall. MemOS, with the highest recall, has the best QA (67.23% Medium, 64.44% Long); Mem0 falls to 28.11% on Long.
   - Histories run ~1.5k (Medium) and ~2.6k (Long) turns per user, over 1M tokens.
   - [HaluMem](https://arxiv.org/html/2511.03506)
10. Letta's agent on the raw conversation file plus grep and semantic file search: 74.0% on LoCoMo vs Mem0g's 68.5 [vendor, Aug 2025] — [Letta benchmark post](https://www.letta.com/blog/benchmarking-ai-agent-memory)

**Evidence that extracted or derived structure helps**
- On long histories Zep beats full context: LongMemEval_S 71.2 vs 60.2 (gpt-4o) and 63.8 vs 55.4 (gpt-4o-mini). The biggest gains are single-session-preference (+23.3 / +36.7 points, computed) and temporal reasoning (+17.6 / +17.3) — [Zep paper](https://arxiv.org/html/2501.13956)
- Long-context reading degrades badly. With oracle sessions vs the full LongMemEval_S history, GPT-4o drops 0.870 → 0.606 and Llama 3.1 70B drops 0.744 → 0.334. ChatGPT (GPT-4o) scored 0.577 vs 0.918 for offline GPT-4o in the commercial test — [LongMemEval](https://arxiv.org/html/2410.10813)
- LongMemEval also reports that time-aware query expansion lifts temporal-reasoning recall by ~11.3% (rounds) and 6.8% (sessions), but only when a strong LLM extracts the time ranges. Chain-of-Note plus JSON formatting improves reading by up to 10 points — [LongMemEval](https://arxiv.org/html/2410.10813)
- Facts as values help multi-session reasoning (LongMemEval), and observations beat raw dialog at a fixed small k for a weak reader (LoCoMo) — [LongMemEval](https://arxiv.org/html/2410.10813); [LoCoMo paper](https://arxiv.org/html/2402.17753)
- Mem0's own run of raw-chunk RAG with k ≤ 2 scored 36.84–60.97 J, below Mem0's 66.88 — [Mem0 paper](https://arxiv.org/html/2504.19413). LightMem's run disagrees: NaiveRAG 63.64 > Mem0 61.69 on LoCoMo and 61.00 > 53.61 on LongMemEval-S — [LightMem paper](https://arxiv.org/html/2510.18866)

**What each storage choice gains and loses**

| System | Stores | Gains | Loses |
|---|---|---|---|
| Zep | Raw episodes + fact graph | +8.4 / +11.0 points over full context on LongMemEval_S; 1.6k vs 115k context tokens; latency 2.58–3.20 s vs 28.9–31.3 s ([Zep](https://arxiv.org/html/2501.13956)) | −6.8 / −14.2 points on single-session-assistant ([Zep](https://arxiv.org/html/2501.13956)); footprint ">600k tokens" (Mem0's disputed claim) ([Mem0](https://arxiv.org/html/2504.19413)) |
| Mem0 | Facts only | 1,764 vs 26,031 tokens; total p95 1.44 vs 17.12 s ([Mem0](https://arxiv.org/html/2504.19413)) | −6.0 J vs full context ([Mem0](https://arxiv.org/html/2504.19413)); 3.23% extraction recall on HaluMem-Long ([HaluMem](https://arxiv.org/html/2511.03506)); 26.8 on single-session-assistant ([MemOS](https://arxiv.org/html/2507.03724)) |
| A-MEM | Raw + LLM metadata + links | 85–93% fewer tokens per operation; 62.60 > FullText 56.80 on LongMemEval-S in LightMem's run ([A-MEM](https://arxiv.org/html/2502.12110); [LightMem](https://arxiv.org/html/2510.18866)) | 13.0 LLM calls per response in MemoryOS's run ([MemoryOS](https://arxiv.org/html/2506.06326)); 48.38 J in Mem0's run ([Mem0](https://arxiv.org/html/2504.19413)) |
| MemGPT / Letta | Raw history + agent-curated core memory | Raw file + search: 74.0% on LoCoMo ([Letta](https://www.letta.com/blog/benchmarking-ai-agent-memory)) | 16,977 tokens and 4.3 calls per response ([MemoryOS](https://arxiv.org/html/2506.06326)); 28.3 overall on MemoryAgentBench ([MAB](https://arxiv.org/html/2507.05257)) |
| LightMem | Compressed raw + summaries | Online tokens up to 117× fewer; 68.64 on LongMemEval-S ([LightMem](https://arxiv.org/html/2510.18866)) | 32.14 vs 98.21 (NaiveRAG) on single-session-assistant ([LightMem](https://arxiv.org/html/2510.18866)) |
| MIRIX | Six typed LLM-written stores | 99.9% less storage than RAG on screenshots ([MIRIX](https://arxiv.org/html/2507.07957)) | −2.14 vs full context on LoCoMo (computed) ([MIRIX](https://arxiv.org/html/2507.07957)) |

**Benchmark reliability (affects every number above)**
- **LoCoMo size:** 50 conversations, ~300 turns, ~19.3 sessions and ~9.2k tokens each in the original paper — [LoCoMo paper](https://arxiv.org/html/2402.17753). Mem0 says the raw conversation is ~26k tokens — [Mem0](https://arxiv.org/html/2504.19413). Zep says 16k–26k — [Zep rebuttal](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/). Either way it fits in modern context windows.
- **Re-run spread:**

  | System | LoCoMo scores reported by different teams |
  |---|---|
  | Zep | 59.22 (MemOS), 65.99 (Mem0), 75.14 (Zep), 79.09 (MIRIX, other backbone) |
  | Mem0 | 61.69 (LightMem), 62.47 (MIRIX), 64.57 (MemOS), 66.88 (Mem0) |
  | Full context | 71.83 (LightMem, gpt-4o-mini), 72.90 (Mem0, gpt-4o-mini), 74.87 (LightMem, Qwen3), 87.52 (MIRIX, gpt-4.1-mini) |

  [Mem0](https://arxiv.org/html/2504.19413); [Zep rebuttal](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/); [MIRIX](https://arxiv.org/html/2507.07957); [MemOS](https://arxiv.org/html/2507.03724); [LightMem](https://arxiv.org/html/2510.18866)
- **Category labels** are permuted between the A-MEM and Mem0 papers (§3), so per-category LoCoMo comparisons across papers are unsafe — [A-MEM](https://arxiv.org/html/2502.12110); [Mem0](https://arxiv.org/html/2504.19413)
- **The adversarial (category 5) questions are excluded** by Mem0 and Zep ("ground-truth answers are missing") and by Memory-R1 — [Zep rebuttal](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/); [Memory-R1](https://arxiv.org/html/2508.19828)

### Inferences
- **The best-supported design is "raw as the value, extracted facts as keys and pointers".** LongMemEval's K = raw + fact result, A-MEM's content-plus-metadata, Zep's episodes-plus-facts and Letta's recall-plus-core memory all keep raw text. The systems that discard it (Mem0, Memobase, MemU, Memory-R1's fact bank) lose details, assistant-side content and long-run recall.
- **Without embeddings, BM25 is not a big handicap for accurate retrieval.** In MemoryAgentBench it scored 60.5 on accurate retrieval, above Text-Embed-3-Small (53.8) and, in the paper's words, "outperforming most embedding-based methods". The scores of the stronger embedders in that comparison (Text-Embed-3-Large, Qwen3-Embedding-4B) weren't captured in my fetch. Those tasks (single- and multi-hop document QA, EventQA, LongMemEval-S*) test retrieval over text, not paraphrase robustness. What embeddings mostly buy is paraphrase robustness, and LongMemEval-style key expansion supplies some of that lexically: index each raw turn under its own words plus the extracted statements and subjects. LongMemEval's numbers used a dense retriever; I found no BM25 numbers for the key-expansion experiment.
- **Coding-agent analogue of the single-session-assistant failure.** In Claude Code, much of what matters is said by the assistant: what it proposed, implemented, rejected and why. Extraction pipelines centred on the user (most of these systems) are the ones that collapse on assistant-side questions. Whatever is extracted, the raw assistant turns must stay searchable.
- **When the whole history fits, reading it beats retrieval** (LoCoMo results). The retrieval advantage appears at ~100k+ tokens (LongMemEval_S), where long-context reading degrades by 30–55%. For small projects, loading curated notes and grepping raw logs is a strong baseline.
- **Updates should be append-only invalidation, not DELETE.** Zep uses `t_invalid` and Mem0g marks relations invalid. HaluMem shows the reconcile step's real weakness is missing the old memory (>50% omission), so write-time candidate recall matters as much as the judge.
- **Fit to the stated constraints.** The parts that satisfy "stdlib only, background-only small-model calls, <0.5 s per message" are:
  - BM25 with fielded key expansion, plus n-hop BFS over typed links.
  - RRF/MMR fusion of several lexical rankers (statements, raw turns, recency or heat).
  - Bi-temporal fields with supersession.
  - A rolling-summary-plus-recent-window extraction context.
  - Background consolidation or reflection with citations.

  The parts that need what is unavailable are dense similarity anywhere, cross-encoder reranking, per-query LLM topic or time-range extraction (MIRIX Active Retrieval, LongMemEval time-aware expansion), LLMLingua-2 compression, and KV-cache or LoRA memory.
- **Consistency with this project.** The local held-out result recorded in `tests/PROGRESS.md` (v5 curated notes + grep 0.828, records-first v7 0.792, grep 0.806) fits the literature: extraction-first retrieval doesn't beat raw or curated text plus lexical search unless the raw text is kept as the value and searched alongside.

### Gaps
- I found no truly independent replication of any vendor's headline LoCoMo or LongMemEval number. Third-party numbers come from competitors' papers with their own setups.
- I didn't check the official LongMemEval leaderboard or late-2025/2026 vendor claims.
- No paper isolates BM25 vs dense retrieval in the raw-vs-fact comparison. LongMemEval's appendix comparison of retrievers was not in the fetched text.
- No study measures any of these architectures on coding-agent transcripts (decisions, rejected options, file and line provenance); that is outside this note's scope.
- LoCoMo's per-category full-context numbers are not reported in Mem0's paper, so the category-level raw-vs-fact comparison rests on MIRIX's table (another backbone) and LongMemEval's question types.

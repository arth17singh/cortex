# Lifecycle of LLM agent memory and reliable evaluation of memory systems (2023–2026)

Labels used below: **[vendor]** = written by the company that sells the system (or its founders); **[independent]** = academic or third-party work with no product stake in the result; **[secondary]** = an aggregator, blog or search summary, not the primary paper or code; **[low-quality]** = practitioner blog or unreviewed preprint whose numbers I could not check. "CORTEX" means the end-use setting: a local, file-based, Python-stdlib memory for a coding agent, small-model calls only in the background, scored with blind question sets and an LLM judge. Research done 2026-11-04.

## 1. Consolidation and "sleep-time" processing: what runs offline, and what gains are reported?

### Takeaway
Published systems do three kinds of offline work: (a) summarising or reflecting (Generative Agents reflections, Mem0's async summary, MemoryBank's daily summaries and user portrait), (b) reorganising and deduplicating (LightMem's "sleep-time update", Zep's community refresh), and (c) precomputing likely answers (Letta's sleep-time compute). The reported gains are almost all self-reported and measured on proxies: synthetic stateful maths for sleep-time compute, believability for reflection, and +2–6% on LongMemEval for LightMem (absolute vs relative not stated) after its authors revised the v1 claim of up to +10.9%. I found no independent replication on memory QA.

### Cited Findings
- **Sleep-time compute** [vendor-affiliated: Letta authors plus UC Berkeley; Lin, Snell, Wang, Packer, Wooders, Stoica, Gonzalez; 17 Apr 2025]. Precomputing over a persistent context before the query arrives cuts the test-time compute needed for the same accuracy by about 5x on Stateful GSM-Symbolic and Stateful AIME. Scaling sleep-time compute raises accuracy by up to 13% (GSM-Symbolic) and 18% (AIME). Amortising over related queries about the same context (Multi-Query GSM-Symbolic) cuts average cost per query by 2.5x. The gain correlates with how predictable the query is from the context. The paper also includes an agentic software-engineering case study — [arXiv 2504.13171](https://arxiv.org/abs/2504.13171)
- **Generative Agents reflection** [independent; Park et al., Apr 2023]:
  - **Trigger:** reflection runs when the summed importance scores (an LLM rates each memory 1–10) of the latest perceived events exceed 150, which happened about 2–3 times per simulated day.
  - **Method:** the model reads the 100 most recent memory records, writes 3 salient high-level questions, uses each as a retrieval query, and extracts insights that cite their supporting records. Reflections go back into the memory stream and can themselves be reflected on, forming trees — [arXiv 2304.03442](https://arxiv.org/abs/2304.03442)
- **Generative Agents ablation** (100 Prolific evaluators, TrueSkill rating of believability, not factual accuracy): full architecture μ=29.89 (σ=0.72); no reflection 26.88; no reflection and no planning 25.64; human crowdworkers 22.95; no observation, reflection or planning 21.21. Effect size between the prior-work condition and the full architecture: d=8.16. Memory failure modes named by the authors: failing to retrieve relevant memories, retrieving only part of a memory, and embellishing (adding details that were never discussed, or pulling in world knowledge from the base model) — [arXiv 2304.03442](https://arxiv.org/abs/2304.03442)
- **Mem0** [vendor]: the conversation summary used during extraction is refreshed asynchronously, outside the main write path — [arXiv 2504.19413](https://arxiv.org/abs/2504.19413)
- **Zep** [vendor]: communities are built by label propagation. New nodes join their neighbours' plurality community and that community's summary is updated incrementally. The authors say incremental communities drift from a full label-propagation run, so periodic full refreshes are still needed — [arXiv 2501.13956](https://arxiv.org/abs/2501.13956)
- **LightMem** [independent academic, self-reported; ICLR 2026; numbers from a search summary of arXiv v3/v4, paper not read in full]:
  - **Method:** new entries are stored with timestamps as immediate "soft" updates. During offline "sleep" periods the system reorganises, de-duplicates and abstracts them, resolving inconsistencies.
  - **Latest version:** LongMemEval accuracy +2.09 to +6.40% over the strongest baseline with GPT, up to +7.67% with Qwen (absolute vs relative not stated in the summary). Counting online and offline work together, total tokens fall up to 38x (GPT) and 21.8x (Qwen) and API calls up to 30x and 17.1x.
  - **v1:** claimed up to +10.9% accuracy, 117x fewer tokens and 159x fewer API calls. The later versions use the lower, offline-inclusive figures — [arXiv 2510.18866](https://arxiv.org/abs/2510.18866)
- **MemoryOS** [independent academic, self-reported; Kang et al., 30 May 2025]:
  - **Structure:** short-term, mid-term and long-term personal memory. Short→mid follows a "dialogue-chain-based FIFO principle"; mid→long uses segmented page organisation.
  - **Reported result:** average improvements of 49.11% F1 and 46.18% BLEU-1 on LoCoMo over baselines with GPT-4o-mini. These are relative gains on lexical metrics, not an LLM judge — [arXiv 2506.06326](https://arxiv.org/abs/2506.06326)
- **MemOS** [independent academic consortium; v1 Jul 2025, v4 Dec 2025]: the "MemCube" unit carries content plus provenance and versioning metadata. MemCubes can be composed, migrated and fused across plaintext, activation and parameter memory. The abstract reports no benchmark numbers — [arXiv 2507.03724](https://arxiv.org/abs/2507.03724)
- **"Filesystem is all you need"** [vendor: Letta blog, 12 Aug 2025]:
  - **Result:** a Letta agent with file tools (grep, search_files, open, close; gpt-4o-mini; minimal prompt tuning) scored **74.0%** on LoCoMo, against the **68.5%** Mem0 reported for its best graph variant.
  - **Caveat:** the history was uploaded as a single file that Letta also embeds for semantic search, so this was not pure grep.
  - **Authors' conclusions:** memory benchmarks "may not be very meaningful", and whether an agent can use a retrieval tool effectively matters more than the retrieval mechanism — [Letta blog](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- **MemoryAgentBench** [independent; Hu, Wang, McAuley, UCSD; v4 dated Jun 2026]: on Accurate Retrieval, plain BM25 averages 60.5, above long-context GPT-4o-mini at 49.2 (HippoRAG-v2 65.1; long-context GPT-5-mini 74.4). On Test-Time Learning and Long-Range Understanding, long-context models beat every RAG or memory agent (LRU: GPT-5-mini 66.2 vs best memory agent 40.5, Mem0 20.7, Zep 16.2) — [arXiv 2507.05257](https://arxiv.org/abs/2507.05257)

### Inferences
- The evidence that offline consolidation improves factual recall is thin. The cleanest result (sleep-time compute) is on synthetic maths with a fixed context. Reflection was measured for believability. LightMem's and MemoryOS's gains are self-reported, and LightMem revised its own headline down by about half between versions.
- Sleep-time compute pays off when queries are predictable from the stored context. In a coding project the predictable queries are "what is the current decision on X", "what was rejected for X and why", and "what depends on X". Precomputing per-subject current-state pages in the background (CORTEX's entities.md, rendered after each write) is the closest analogue. It only amortises if the same subjects are asked about repeatedly.
- **For CORTEX:**
  - The backfill-time open-item resolution pass and the explicit-supersession linking are CORTEX's sleep-time consolidation. Treat each as an intervention measured before and after on a fresh question set, not as an assumed win.
  - Zep's drift note suggests the same will happen to CORTEX's incremental subject canonicalisation. A periodic full re-canonicalisation with a diff (background, small model) is the analogue of Zep's full community refresh.
  - Letta's filesystem result and MemoryAgentBench's strong BM25 retrieval match CORTEX's own finding that grep over curated notes is competitive. Consolidation should make the reader's iterative search better (well-indexed records that link to session-log lines), not replace reading.
  - Generative Agents' embellishment failure argues for keeping consolidated outputs (summaries, "Resolved:" records) as separate, provenance-linked records that never overwrite their sources. CORTEX's append-only design already does this.

### Gaps
- No independent replication of sleep-time compute on conversational or coding-memory QA was found.
- LightMem's per-configuration LongMemEval table was not read; the numbers come from a search summary of the arXiv pages.
- MemoryOS's heat-based mid-term eviction formula and its isolated effect were not confirmed (not in the abstract).
- Letta's sleep-time agent product docs were not read (skipped for budget). Only the research paper is cited.
- I found no study that measures how often consolidated summaries or reflections introduce errors (the Generative Agents embellishment examples are qualitative).

## 2. Deduplication and conflict resolution: how do Mem0 and Zep/Graphiti decide that a new fact contradicts an old one, and how accurate is it?

### Takeaway
Both vendors use the same basic design. A small candidate set is retrieved by similarity (Mem0: top-10 by vector; Graphiti: hybrid search, restricted to the same entity pair when checking duplicates). One LLM call then labels each candidate as duplicate, contradiction or neither, and history is kept rather than deleted (Mem0g marks edges invalid; Graphiti sets `invalid_at`/`expired_at`). Neither publishes the accuracy of these decisions. The only independent measurement I found, MemoryAgentBench's FactConsolidation, shows every memory system doing badly at overwrite resolution: Mem0 averages 10.0 and Zep 5.0, against 25.5 for plain BM25 and 32.5 for long-context GPT-4o. Multi-hop is at most 28% for every system.

### Cited Findings
- **Mem0 pipeline** [vendor; Chhikara et al., Apr 2025]:
  - **Extraction:** a small model sees the conversation summary, the last m=10 messages and the new message pair, and extracts candidate facts.
  - **Update:** for each candidate fact, the top s=10 similar memories are retrieved by embedding. The LLM then chooses ADD, UPDATE, DELETE or NOOP through a function-calling tool interface, with no separate classifier.
    - ADD: no equivalent memory exists.
    - UPDATE: augments an existing memory, applied only when the new fact carries more information.
    - DELETE: the memory is contradicted by the new information.
    - NOOP: no change.
  - **Mem0g (graph):** entities are matched to existing nodes by similarity above a threshold. An LLM "update resolver" decides whether conflicting relationships are obsolete, and obsolete relationships are **marked invalid rather than deleted**, to support temporal reasoning — [arXiv 2504.19413](https://arxiv.org/abs/2504.19413)
- **Mem0 publishes no accuracy, precision or recall** for its ADD/UPDATE/DELETE/NOOP decisions, its contradiction checks or the Mem0g resolver. The only evidence is end-to-end LoCoMo QA — [arXiv 2504.19413](https://arxiv.org/abs/2504.19413)
- **Mem0's LoCoMo results** [vendor]. Setup: the 10-conversation release, about 200 questions each; adversarial category excluded "because ground-truth answers were unavailable"; judge described only as "a separate, more capable LLM"; 10 runs, mean ± 1 SD.

  | System | Overall J |
  |---|---|
  | Full-context | 72.90 ± 0.19 |
  | Mem0g | 68.44 ± 0.17 |
  | Mem0 | 66.88 ± 0.15 |
  | Zep | 65.99 ± 0.16 |
  | Best RAG (k=2, chunk 256) | 60.97 |
  | LangMem | 58.10 |
  | OpenAI memory | 52.90 |
  | A-Mem | 48.38 |

  p95 latency: Mem0 1.44 s vs full-context 17.12 s. Memory tokens per query: Mem0 1,764 vs full-context 26,031. Mem0's own best system is below full context — [arXiv 2504.19413](https://arxiv.org/abs/2504.19413)
- **The LoCoMo scores are disputed between vendors.** Zep's blog says Mem0 misconfigured Zep and reports Zep at 75.14% ± 0.17 when run correctly; Zep also argues LoCoMo itself is flawed and prefers LongMemEval [vendor; seen via search snippet, page not fetched] — [Zep blog](https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/). Mem0's counter-claim appears only in secondary sources; see Gaps.
- **Zep's bi-temporal model** [vendor; Rasmussen et al., Jan 2025]. Every edge carries four timestamps on two timelines:
  - **T (event time):** `t_valid` and `t_invalid`, the period when the fact held true.
  - **T′ (transaction time):** `t′_created` and `t′_expired`, when the system ingested or invalidated it.

  How invalidation works:
  - An LLM compares each new edge with semantically related existing edges.
  - An existing edge is invalidated only when the contradiction overlaps in time; its `t_invalid` is set to the new edge's `t_valid`.
  - New information wins on the T′ timeline — [arXiv 2501.13956](https://arxiv.org/abs/2501.13956)
- **Zep's entity and fact deduplication** [vendor]:
  - **Entities:** each new entity name is embedded (1024-d) and matched by cosine plus full-text search over names and summaries. An LLM, given the episode context, decides whether it duplicates an existing entity and writes the merged name and summary.
  - **Facts:** deduplication searches only edges between the same entity pair, "which limits errors and computational cost". Facts need not be identical, only express the same information.
  - **Writes:** graph writes use predefined Cypher queries, not LLM-generated ones — [arXiv 2501.13956](https://arxiv.org/abs/2501.13956)
- **Graphiti code** (getzep/graphiti `main`, read 2026-11-04; may differ from the version in the 2025 paper):
  - **Candidates:** `resolve_extracted_edges` runs two hybrid searches (RRF) with the new fact's embedding. One is filtered to edges between the same two endpoints (duplicate candidates); the other is unfiltered (invalidation candidates).
  - **Shortcuts before the LLM:** exact normalised-text matches are reused without a model call.
  - **LLM call:** one small-model call (`dedupe_edges.resolve_edge`) returns `duplicate_facts` and `contradicted_facts`.
  - **Timestamps:** `created_at` is set once and never changed by invalidation. When periods overlap and an older candidate started earlier, the candidate gets `invalid_at = new.valid_at` and `expired_at = now`. If an already-stored **contradicting** edge (one the LLM flagged) starts later than the new one (out-of-order ingestion), the new edge itself gets `invalid_at = candidate.valid_at`. Edges whose periods don't overlap, or that lack dates, are left alone — [edge_operations.py](https://raw.githubusercontent.com/getzep/graphiti/main/graphiti_core/utils/maintenance/edge_operations.py)
- **Graphiti's contradiction prompt** (`main`, read 2026-11-04):
  - **Contradiction:** only when the new fact and the old one "cannot both be true", and only with "explicit evidence that the old fact stopped being true or was replaced" (termination, replacement, transfer, or mutually exclusive current-state language).
  - **Not contradiction:** recency alone, episode or meeting dates, weekly snapshots, or "updates" headings.
  - **Coexistence rule:** role, ownership and responsibility facts are not contradicted by work, progress or blocker updates on the same project.
  - **Duplicates:** never mark facts as duplicates when numbers, dates or key qualifiers differ — [dedupe_edges.py](https://raw.githubusercontent.com/getzep/graphiti/main/graphiti_core/prompts/dedupe_edges.py)
- [secondary] Third-party write-ups of the code agree that `invalid_at` records when a fact stopped being true and `expired_at` when the system learned it. Time-scoped queries return edges with `valid_at` ≤ query time and `invalid_at` later or null — [DeepWiki temporal model](https://deepwiki.com/wikiw2025/graphiti/3.3-temporal-model). A Zep platform changelog (Jun 2026) notes that setting `valid_at`/`invalid_at` to null via `graph.edge.update` now clears them — [Zep changelog](https://help.getzep.com/changelog/2026/6/25)
- **Zep on LongMemEval_S** [vendor], against full context, gpt-4o-mini / gpt-4o:
  - **Overall:** 63.8% vs 55.4% and 71.2% vs 60.2%. The "15.2%/18.5%" headline gains are relative; the absolute gains are +8.4 and +11.0 points.
  - **Cost:** about 1.6k vs 115k context tokens, and about 90% lower latency.
  - **Knowledge-update** (the category that tests overwriting): got worse with gpt-4o-mini (76.9 → 74.4) and better with gpt-4o (78.2 → 83.3).
  - **Single-session-assistant:** got worse with both models (81.8 → 75.0; 94.6 → 80.4). The authors call this a notable exception.
  - **Internal inconsistencies in the paper:** top-10 vs top-20 retrieved items are stated in different sections, and the gpt-4o single-session-user row duplicates the gpt-4o-mini row — [arXiv 2501.13956](https://arxiv.org/abs/2501.13956)
- **MemoryAgentBench FactConsolidation** [independent; Jun 2026 v4]:
  - **Setup:** MQuAKE counterfactual edit pairs, with the rewritten (contradicting) fact placed after the original, in 6K–262K-token contexts. Agents are told that "newer facts have larger serial numbers".
  - **Scores** (single-hop / multi-hop / average):

    | System | SH | MH | Avg |
    |---|---|---|---|
    | Long-context GPT-5-mini | 78 | 28 | 53.0 |
    | Long-context GPT-4o | 60 | 5 | 32.5 |
    | HippoRAG-v2 | 54 | 5 | 29.5 |
    | BM25 | 48 | 3 | 25.5 |
    | MemGPT | 28 | 3 | 15.5 |
    | Cognee | 28 | 3 | 15.5 |
    | Mem0 | 18 | 2 | 10.0 |
    | Zep | 7 | 3 | 5.0 |

  - **Reasoning model:** o4-mini reaches 100 SH and 80 MH at 6K, but only 61 and 14 at 32K.
  - **Authors' conclusion:** "all methods fail on the multi-hop situation", and forgetting out-of-date memory "poses a significant challenge" — [arXiv 2507.05257](https://arxiv.org/abs/2507.05257)

### Inferences
- **Candidate retrieval caps conflict-detection recall.** A contradiction the candidate search never surfaces is never judged (Mem0 sees only the top-10 similar memories; Graphiti dedupes only within the same entity pair). Recall therefore depends on subject and entity linking quality. CORTEX's near-duplicate-name gate (exit 4) and subject canonicalisation sit exactly at this choke point.
- **The FactConsolidation result has two readings.** Either the LLM-update pipelines lose the "newest wins" signal when facts arrive as long chunks, or they never compare the right pair. In both cases the reader cannot be trusted to resolve conflicts from raw context, especially multi-hop consequences of a change. Explicit supersession chains and showing only current records are the defensible design. The benchmark's format (counterfactual facts with serial numbers) is unlike conversational ingestion, so the absolute numbers may understate vendor systems on their native inputs.
- **For CORTEX:**
  - **Field mapping.** CORTEX's `valid_from`/`valid_to` map to Graphiti's `valid_at`/`invalid_at` (event time), and `recorded_at` maps to `created_at`. There is no explicit transaction-time "expired_at" (when memory learned the old record was wrong). In an append-only log it can be derived from the superseding record's `recorded_at`. If `valid_to` is ever written in place without that link, "what did memory say on date D" becomes unanswerable, which matters for auditing eval runs and for replaying backfills.
  - **Adopt Graphiti's criteria in the conflict judge.** They are a ready-made, published rule set to put into the Haiku judge prompt that decides supersedes / coexists / duplicate: "cannot both be true", explicit termination or replacement evidence, no contradiction from recency alone, ownership coexists with progress, and numeric or date differences are never duplicates. They line up with CORTEX's type-aware conflict thresholds.
  - **Handle out-of-order ingestion.** Graphiti compares `valid_at` dates, not ingestion order, and closes a new fact when an already-stored contradicting fact is later in event time. CORTEX's backfill writes chronologically, but live capture and later backfills can interleave, so supersession should compare `valid_from`, never `recorded_at`.
  - **No vendor accuracy to borrow.** CORTEX must measure its own update-decision precision and recall on labelled pairs; the synthetic corpus with planted supersessions, rejections and near-duplicate names is the natural set. Its own audit (5 of 21 explicit-supersession candidates linked; 1 of 3 known plan supersessions chained) is already more measurement than either vendor publishes.

### Gaps
- No published accuracy (precision, recall or agreement with humans) for Mem0's four-way update decision, Mem0g's resolver, or Zep/Graphiti's invalidation step.
- Mem0's reported rebuttal also appeared only in a search summary; I could not identify the page it came from. In that summary, Mem0's co-founder says Zep's figure included the adversarial category and that Zep scores 58.44% ± 0.20 on categories 1–4, and an earlier "84%" Zep claim is disputed. The Zep blog's exact date was not confirmed either.
- Graphiti's `EDGE_HYBRID_SEARCH_RRF` top-k limits were not read.
- No study measures how often LLM conflict judges wrongly invalidate facts that should coexist (the false-supersession rate), which is the failure that silently deletes valid memory.

## 3. Forgetting and decay: does Ebbinghaus-style decay, importance or recency help or hurt factual recall?

### Takeaway
Decay is a design heuristic that has never been shown to help factual recall. MemoryBank's Ebbinghaus model was not ablated, and its authors call it "exploratory and highly simplified". Generative Agents' recency term (0.995 per game hour) was tuned for believability and never ablated on its own. The best controlled evidence on deletion (Xiong et al., 2025) shows quality-gated **addition** helps a lot (+15 to +25 points across four agents). Deletion helps only modestly, and only with an accurate quality evaluator; periodic, time-based deletion mostly hurts.

### Cited Findings
- **MemoryBank** [independent; Zhong et al., 17 May 2023]:
  - **Model:** retention R = e^(−t/S). Strength S starts at 1 on first mention; each time a memory is recalled, S increases by 1 and elapsed time t resets to 0, "hence forget it with a lower probability".
  - **Authors' caveat:** "an exploratory and highly simplified memory updating model".
  - **Motivation:** forgetting "can make the AI companion more natural".
  - **Evaluation:** 194 hand-written probing questions (97 English, 97 Chinese) over 10 days of ChatGPT-simulated chats with 15 virtual users, comparing three base LLMs.
  - **No ablation:** the paper only claims "applicability with and without memory forgetting mechanism", and no experiment isolates the forgetting mechanism's effect on recall — [arXiv 2305.10250](https://arxiv.org/abs/2305.10250)
- **Generative Agents retrieval** [independent; 2023]: retrieval score = recency + importance + relevance, each min-max normalised to [0,1], all weights α=1.
  - Recency: exponential decay with factor 0.995 per game hour since the memory was last retrieved.
  - Importance: an LLM rating from 1 to 10 at creation time.
  - Relevance: embedding cosine.

  The ablations remove reflection, planning and observation, never the recency or importance terms — [arXiv 2304.03442](https://arxiv.org/abs/2304.03442)
- **Experience-following study** [independent; Xiong et al., May 2025, rev. Oct 2025]. Agents copy the outputs of retrieved memories whose inputs resemble the current task, so bad stored experiences propagate errors.
  - **Strict selective addition vs add-all:**

    | Agent | Add-all | Strict | Gain |
    |---|---|---|---|
    | RegAgent | 55.48 | 70.95 | +15.47 |
    | EHRAgent | 13.05 | 38.50 | +25.45 |
    | AgentDriver | 32.32 | 51.00 | +18.68 |
    | CIC-IoT | 59.90 | 85.40 | +25.50 |

    Add-all memories also grew much larger (EHRAgent 2,411 vs 1,012 records).
  - **Deletion with a strict evaluator:** history-based deletion: EHRAgent +3.39, AgentDriver +0.81, CIC-IoT +4.20, RegAgent −1.15. Periodic deletion: RegAgent −3.30, EHRAgent −0.08, AgentDriver −0.06, CIC-IoT −4.60.
  - **Deletion with a coarse evaluator:** sometimes hurt (AgentDriver history −2.92; CIC-IoT combined −5.20).
  - **Authors' conclusion:** the effect of deletion "varies notably across evaluators based on LLMs without fine-tuning" — [arXiv 2505.16067](https://arxiv.org/abs/2505.16067)
- **MemoryAgentBench** names its overwrite competency "Selective Forgetting" (newer facts must override older ones) and finds every system weak at it; see section 2 — [arXiv 2507.05257](https://arxiv.org/abs/2507.05257)
- **Decay used for security, not recall** [independent; Jan 2026; via search summary, paper not fetched]: one memory-poisoning defence uses "trust-aware retrieval with temporal decay" as part of memory sanitisation — [arXiv 2601.05504](https://arxiv.org/abs/2601.05504)
- **Recency as a requirement:** LongMemEval's knowledge-update category explicitly needs the latest value preferred over older ones — [arXiv 2410.10813](https://arxiv.org/abs/2410.10813)

### Inferences
- **Separate validity from time.** "Old" and "wrong" are different things. Recency helps when a value has been updated (knowledge-update questions) but would hurt stable facts: in a coding project, a 3-month-old architecture decision that was never superseded is still true. Explicit validity (superseded or not) is the safer signal, with recency only as a tie-breaker among current records on the same subject.
- **For CORTEX:**
  - The bigger lever is the capture gate's precision (Xiong's "strict addition"), not pruning.
  - Delete or close records only on reliable signals: an explicit supersession, a resolved open item, or a user rejection. Never on age, the analogue of periodic deletion that lost up to 4.6 points.
  - The 82 never-closed `open` records found in the failure analysis are the "misaligned experience" problem (stale items shown next to their resolution). The background resolution pass is the right fix, provided its judge is measured, since an inaccurate evaluator made deletion hurt in Xiong's study.
  - An Ebbinghaus-style "strength" can still be useful as a ranking feature: recalled-and-used records are likely important. It should never hide a record from search.

### Gaps
- I found no controlled study isolating time decay (Ebbinghaus or exponential recency) on factual QA accuracy, in either direction.
- MemoryOS's heat-based eviction has not been ablated in anything I read.
- No study on decay in coding-agent memory specifically.

## 4. Abstention and unanswerable questions: what do LongMemEval, LoCoMo and RAG research show, and which signals predict that the answer is absent?

### Takeaway
Abstention is the least-measured part of memory evaluation:
- LongMemEval has only 30 abstention questions out of 500.
- LoCoMo's adversarial category (about 25% of its questions) is routinely excluded, Mem0's paper included.
- Its commercial-assistant study used a dataset version with no abstention questions at all.

What evidence exists says that more retrieved context makes abstention worse. LoCoMo's adversarial F1 falls as top-k grows. Adding RAG context cut Gemini 1.5 Pro's abstention rate from 100% to 18.6% in the Sufficient Context study, while models still answer correctly 35–62% of the time from insufficient context. The best-supported signal combines an LLM "sufficient context" label with the model's own confidence in a small logistic regression, thresholded for a target coverage; it gives +2 to +10% accuracy among answered questions. Retrieval-score thresholds alone look weak, but that evidence is low quality.

### Cited Findings
- **LongMemEval composition** [independent; Wu et al., Oct 2024]: 500 questions over five abilities. Abstention questions are 30 "false premise" questions made by modifying answerable questions from the other types so the answer is unknown. Settings: LongMemEval_S (about 115k tokens) and LongMemEval_M (about 500 sessions, 1.5M tokens) — [arXiv 2410.10813](https://arxiv.org/abs/2410.10813)
- **LongMemEval judge on abstention:** the GPT-4o judge's meta-evaluation was weakest on abstention (0.97, 29/30, on GPT-4o answers; 0.90, 27/30, on Llama-3.1-8B answers) and on single-session-preference, "due to the open-ended nature of the response". The commercial-assistant analysis (ChatGPT 0.5773, Coze 0.3299, vs 0.9184 offline GPT-4o) used "an early version of the dataset without any abstention questions" — [arXiv 2410.10813](https://arxiv.org/abs/2410.10813)
- **LoCoMo** [independent; Maharana et al., Feb 2024]:
  - **Paper version:** 50 conversations, about 305 turns and 9.2k tokens each, 7,512 QA. Adversarial questions are 1,871 (24.9%), "designed to trick the agent into providing wrong answers"; the correct response identifies the question as unanswerable.
  - **Adversarial F1:**

    | Setting | Adversarial F1 |
    |---|---|
    | Human | 89.4 |
    | GPT-4-turbo (base) | 70.2 |
    | GPT-3.5-turbo (base) | 12.8 |
    | GPT-3.5-turbo-16K, 4K context | 13.1 |
    | GPT-3.5-turbo-16K, 16K context | 2.1 |
    | RAG over dialogs, top-5 → top-50 | 31.9 → 17.0 |
    | RAG over observations, top-5 → top-50 | 44.7 → 27.7 |

  - **Authors' explanation:** LLMs "can be easily misled into generating hallucinations when they are subjected to long contexts" — [arXiv 2402.17753](https://arxiv.org/abs/2402.17753)
- **Mem0's LoCoMo is smaller than the paper's.** Mem0 describes LoCoMo as 10 conversations of about 200 questions each (the paper reports 50 conversations and 7,512 QA). Mem0's evaluation excluded the adversarial category entirely "because ground-truth answers were unavailable" — [arXiv 2504.19413](https://arxiv.org/abs/2504.19413)
- **Sufficient Context** [independent: Google; Joren et al., v1 Nov 2024, v3 Apr 2025]:
  - **Definition:** context is sufficient "if and only if there exists an answer A′ such that A′ is a plausible answer to the question Q given the information in C". No ground truth is needed.
  - **Autoraters on 115 human-labelled instances:**

    | Autorater | Accuracy | F1 | Needs ground truth |
    |---|---|---|---|
    | Gemini 1.5 Pro, 1-shot | 0.930 | 0.935 | no |
    | Gemini 1.5 Pro, 0-shot | 0.870 | 0.878 | no |
    | FLAMe (24B; 1,600-token chunks, sufficient if any chunk is) | 0.878 | 0.892 | no |
    | TRUE-NLI | 0.826 | 0.818 | yes |
    | "contains ground truth" | 0.809 | 0.810 | yes |

    — [arXiv 2411.06037](https://arxiv.org/abs/2411.06037)
- **Sufficient Context outcomes** (human-labelled subset, % correct / abstain / hallucinate):

  | Model | Sufficient context | Insufficient context |
  |---|---|---|
  | Gemini 1.5 Pro | 84.1 / 1.6 / 14.3 | 9.6 / 50.0 / 40.4 |
  | GPT-4o | 82.5 / 4.8 / 12.7 | 23.1 / 61.5 / 15.4 |
  | Claude 3.5 Sonnet | 85.7 / 11.1 / 3.2 | 9.6 / 53.8 / 36.5 |
  | Gemma 27B | 71.4 / 3.2 / 25.4 | 9.6 / 55.8 / 34.6 |

  Across datasets, SOTA models answered correctly "35–62%" of the time with insufficient context (from parametric knowledge). Adding retrieval lowered abstention: Claude 3.5 Sonnet 84.1% → 52%, GPT-4o 34.4% → 31.2%, Gemini 1.5 Pro 100% → 18.6%. The extracted text does not say which dataset these come from — [arXiv 2411.06037](https://arxiv.org/abs/2411.06037)
- **Sufficient Context selective generation:**
  - **Method:** the model's self-rated confidence (P(True) from 20 samples for open models; verbalised P(Correct) for proprietary ones) and the binary FLAMe sufficiency label feed a logistic regression. The model abstains when the score falls below a threshold chosen for a target coverage.
  - **Gains:** +2–10% accuracy among answered questions (over 10% for Gemma 27B on HotpotQA in the high-accuracy region; over 5% for Gemini 1.5 Pro near 70% coverage).
  - **Fine-tuning does not fix it:** fine-tuning Mistral-7B to say "I don't know" did not help. Abstention fell to 0–2.2% and hallucination rose (Musique 59.4% → up to 68.6%). The authors conclude fine-tuned models "still hallucinate more often than they abstain" — [arXiv 2411.06037](https://arxiv.org/abs/2411.06037)
- **Retrieval-score signals** [low-quality]:
  - An unreviewed preprint reports that "distribution-shape" features of the retrieval scores detect adversarial unanswerable queries better than a comparison method (0.934 vs 0.864), because unanswerable queries give flat score distributions — [arXiv 2609.11646](https://arxiv.org/pdf/2609.11646)
  - A practitioner blog argues global score thresholds fail and per-query-class thresholds do better, suggesting the top score plus its gap to the next candidate — [tianpan.co blog](https://tianpan.co/blog/2026-04-16-rag-retrieval-abstention-empty-corpus)

### Inferences
- **More context means less abstention.** Two independent sources agree that adding or widening retrieved context lowers abstention: LoCoMo's adversarial F1 falls monotonically with top-k and context length, and the Sufficient Context abstention rates drop when RAG is added. For an injection hook this argues for a **small** pack when retrieval is weak, and for injecting nothing, or an explicit "no matching record", rather than near-miss records. CORTEX's ≤300-token cap and "silent for unrelated" behaviour fit this.
- **Synchronous signals.** In CORTEX the UserPromptSubmit hook cannot afford a 5–7 s model call, so only deterministic signals are available synchronously: the share of query terms matched ("missing-terms"), whether a subject was linked, and the BM25 top score, top-gap and flatness. The Sufficient Context recipe (sufficiency label plus confidence, logistic regression, coverage-set threshold) can be implemented in stdlib with these features plus the answering model's own judgment. It must be fitted on the dev set and validated on fresh questions.
- **The answering model should own abstention.** Fine-tuning for "I don't know" failed in the Google study, so instruction plus evidence is the practical lever. CORTEX's rule (say it isn't recorded only after a second wording and a grep) is a two-signal design in the same spirit.
- **Small abstention sets are not interpretable.** With 10 abstention questions per run, a per-arm accuracy around 0.9 has a standard error of about √(0.9·0.1/10) ≈ 0.095, so ±19 points at 95%. Differences such as v5 .925 vs v7 .875 are not interpretable. Reaching about ±6 points needs roughly 100 abstention or negative questions. LongMemEval's 30 abstention questions carry about ±14 points.
- **Graders tend to be lenient** (section 6), so abstention answers need an explicit grading rule (CORTEX's harness already has NEGATIVE_RULE and an abstention rule keyed on category and group). LongMemEval's judge was least reliable exactly on abstention.

### Gaps
- Per-system abstention accuracy on LongMemEval did not appear in the paper text I could read; it may exist only in figures. No vendor paper (Mem0, Zep) reports abstention separately.
- LoCoMo's exact scoring rule for adversarial answers (string match on "unanswerable" vs F1) is not spelled out in the text read.
- A search summary cited raw retrieval-score features reaching only ROC AUC ≈0.55–0.56 for answerable vs unanswerable classification in two small studies (a 2025 journal paper on SQuAD 2.0 and a demo page). I could not verify the sources, so the figures are not cited as findings.
- Semantic entropy, self-consistency and similar hallucination detectors were not researched for budget reasons.

## 5. Prompt injection via memory or retrieved content, and defences

### Takeaway
Persistent memory turns a one-off injection into a standing one. Three results show the threat is real:
- **AgentPoison:** over 80% attack success with under 0.1% of the memory poisoned.
- **MINJA:** over 95% injection success and 70% attack success through ordinary queries alone (idealised conditions).
- **Moderation:** detection-based moderation and memory sanitisation have been reported largely ineffective against MINJA.

The defences with the strongest numbers are architectural:
- **CaMeL:** untrusted data cannot change control flow; it keeps 77% task success with provable security vs 84% undefended on AgentDojo.
- **Spotlighting:** provenance marking cuts attack success from over 50% to under 2% with GPT models.

### Cited Findings
- **AgentPoison** [independent; Chen, Xiang, Xiao, Song, Li; Jul 2024]: a backdoor attack that poisons an agent's long-term memory or RAG knowledge base. It reaches average attack success above 80% with a poison rate under 0.1% and under 1% impact on benign performance. Tested on an autonomous-driving agent, a knowledge-intensive QA agent and EHRAgent, with no model training needed — [arXiv 2407.12784](https://arxiv.org/abs/2407.12784)
- **MINJA** [independent; Dong et al.; v1 Mar 2025, v5 Feb 2026]: an attacker with only query access plants malicious records that trigger malicious reasoning when a different victim user's query retrieves them. It uses bridging steps, an indication prompt, and "progressive shortening" so the record is retrieved later without the prompt — [arXiv 2503.03704](https://arxiv.org/abs/2503.03704)
- **Follow-up defence study** [independent; Jan 2026; GPT-4o-mini, Gemini-2.0-Flash, Llama-3.1-8B on MIMIC-III; via search summary, paper not fetched]:
  - **Reported MINJA strength:** over 95% injection success and 70% attack success under idealised conditions.
  - **Existing defences:** earlier work found detection-based moderation (e.g. Llama Guard) and memory sanitisation largely ineffective.
  - **Realistic memory weakens the attack:** pre-existing legitimate memories markedly reduce attack effectiveness.
  - **Proposed defences:** composite trust scoring at input and output, and trust-aware retrieval with temporal decay — [arXiv 2601.05504](https://arxiv.org/abs/2601.05504)
- **Spotlighting** [independent; Hines, Lopez, Hall, Zarfati, Zunger, Kiciman; Mar 2024]: a family of prompt transformations that give the model "a reliable and continuous signal of its provenance" for each input source. It cut attack success from over 50% to under 2% with GPT-family models, with minimal task impact — [arXiv 2403.14720](https://arxiv.org/abs/2403.14720)
- **CaMeL** [independent; Debenedetti, Shumailov, …, Carlini, …, Tramèr; v1 Mar 2025, v2 Jun 2025]: extracts control and data flow from the trusted user query so untrusted retrieved data cannot change program flow. Capabilities block private data from flowing out through unauthorised channels. It solves 77% of AgentDojo tasks with provable security vs 84% for an undefended system — [arXiv 2503.18813](https://arxiv.org/abs/2503.18813)
- [secondary] A vendor blog cites Agent Security Bench as reporting a highest average attack success of 84.30% and limited effectiveness of current defences. I did not check the primary source — [vectorize.io](https://vectorize.io/articles/ai-memory-poisoning)

### Inferences
- **CORTEX has a persistence channel.** Its background extractor reads transcripts (which contain tool results: web pages, file contents, command output) and writes records that UserPromptSubmit injects into later prompts. This is the MINJA/AgentPoison pattern: content that entered once is replayed every turn, and the injection hook gives it a privileged slot.
- **Concrete defences for a stdlib, file-based system:**
  1. Extract records only from user and assistant text, never from `tool_result` content (or mark any such record "untrusted").
  2. Reject or flag candidate records whose statement is imperative or instruction-like (e.g. "ignore", "always run", shell commands, URLs to fetch) before cortex_write.
  3. Spotlight the injection block: a delimited data section with per-record provenance tags (`extracted` vs `claude-stated` vs `transcript`) and a standing rule that memory is evidence, not instructions.
  4. Follow CaMeL's principle: memory content never triggers tool calls by itself. Injection is context only, and the guard already restricts writes.
  5. Hold `extracted` records as "unconfirmed" in the injection until corroborated.
- **Measure attack success.** The synthetic corpus already plants an injection. Measuring attack success on it (does the planted instruction reach records.jsonl, and does it reach the injection pack?) is a cheap, judge-free security metric.
- **Moderation alone is weak.** It was reported largely ineffective against MINJA, so a Haiku "is this an injection?" filter should be at most one layer.

### Gaps
- PoisonedRAG's numbers were not verified in this session.
- Agent Security Bench figures come only from a secondary source.
- I found no study of injection persistence in file-based coding-agent memories (e.g. CLAUDE.md or memory files) with measured attack success.

## 6. Evaluation methodology: how reliable are LLM judges (agreement, run-to-run variance, biases, checklist vs holistic grading)?

### Takeaway
On short-answer correctness, strong LLM judges agree with humans 80–97% of the time in raw terms. Raw agreement hides a lot:
- **Leniency:** judges tend to mark answers correct when criteria aren't met (P+ up to 0.99).
- **Score offsets:** 5 to more than 10 points from human scores even at 90%+ agreement.
- **Sensitivity:** smaller judges are sensitive to reference order and can be fooled by "dummy" answers.
- **Self-inconsistency:** LLM judges disagree with themselves across identical runs, and temperature 0 trades that for worse human agreement.

Decomposed checklist grading improves both human agreement and judge-to-judge consistency. Judges rank systems more reliably than they score them. A small human-labelled calibration set (ARES uses ≥150 with prediction-powered inference) turns judge scores into bias-corrected estimates with confidence intervals.

### Cited Findings
- **MT-Bench / Chatbot Arena** [independent; Zheng et al., Jun 2023; NeurIPS 2023 D&B]: strong judges such as GPT-4 reach "over 80% agreement" with human preferences, "the same level of agreement between humans". The paper documents position bias, verbosity bias, self-enhancement bias and limited reasoning ability — [arXiv 2306.05685](https://arxiv.org/abs/2306.05685)
- **"Judging the Judges"** [independent; Thakur et al.; v1 Jun 2024, v6 Aug 2025]:
  - **Setup:** 400 TriviaQA questions, 9 exam-taker models, 13 judges, 3 human annotators, reference-based correct/incorrect grading.
  - **Human baseline:** human–human Scott's π 96.2, 98.52% raw agreement.
  - **Judges:** the best (GPT-4 Turbo, Llama-3 70B, Llama-3.1 70B) reach π in the high 80s; Llama-3 70B is about 8 points behind humans.
  - **Raw agreement misleads:** Llama-3 8B has π 59 with over 80% raw agreement. Judges with π above 80 still assign scores up to 5 points away from human scores, and judges with over 90% raw agreement can be more than 10 points off.
  - **Leniency:** P(marking correct when criteria not met) is well above 0.5 for most judges, e.g. Llama-2-70B 0.99, Gemma-2B and Mistral-7B 0.87.
  - **Other sensitivities:** small judges are sensitive to reference order (an earlier reference makes "correct" more likely); some judges accept dummy answers like "Yes"/"Sure".
  - **Ranks vs scores:** even weak methods rank exam-takers well (Spearman ρ 0.98–0.99 for Contains, Mistral-7B and GPT-4 Turbo), but "identifying which models are better should not be equated to assigning them the correct score". The authors switched from Cohen's κ to Scott's π after finding problems with κ, and recommend reporting π, not raw agreement — [arXiv 2406.12624](https://arxiv.org/abs/2406.12624)
- **"Rating Roulette"** [independent; Haldar & Hockenmaier; Findings of EMNLP 2025; arXiv Oct 2025]:
  - LLM judges have low intra-rater reliability across identical runs, "almost arbitrary in the worst case".
  - Newer, larger models (Qwen 3) are more consistent than Llama 3.1 but still often fall below standard reliability thresholds.
  - Turning off sampling to force identical ratings hurts agreement with humans.
  - Single-run judgments reported without consistency metrics "can be misleading".
  - Structured prompting with explicit evaluation guidelines improved both consistency and human alignment — [arXiv 2510.27106](https://arxiv.org/abs/2510.27106); [ACL Anthology](https://aclanthology.org/2025.findings-emnlp.1361)
- **LongMemEval's judge** [independent]: the GPT-4o judge (gpt-4o-2024-08-06) has "more than 97% agreement with human experts", at least 90% in every setting, and is weakest on preference and abstention questions — [arXiv 2410.10813](https://arxiv.org/abs/2410.10813)
- **TICK** [independent; NeurIPS 2024]: having the judge generate instruction-specific yes/no checklists and answer them raised exact agreement between LLM judgments and human preferences from 46.4% to 52.2%, compared with direct scoring. GPT-4o judge on an internal dataset — [arXiv 2410.03608](https://arxiv.org/abs/2410.03608)
- **CheckEval** [independent; 2024]: decomposed boolean checklists raised average agreement across evaluator models by 0.45 and reduced score variance. Holistic scoring is criticised for lacking "clear decision criteria". The measure is judge–judge consistency, not human agreement — [arXiv 2403.18771](https://arxiv.org/abs/2403.18771)
- **RAGAS** [independent; Es et al., Sep 2023]: reference-free LLM metrics (faithfulness, answer relevance, context relevance) validated on WikiEval by how often the metric prefers the same answer or context as human annotators. Faithfulness was highly accurate; answer relevance was lower because candidate answers often differ subtly. Exact figures not re-verified — [arXiv 2309.15217](https://arxiv.org/abs/2309.15217)
- **ARES** [independent; Saad-Falcon et al., Nov 2023]: fine-tuned lightweight judges, plus a human-annotated validation set of 150 or more datapoints used with prediction-powered inference (PPI), give confidence intervals for RAG scores — [arXiv 2311.09476](https://arxiv.org/abs/2311.09476)
- **Mem0's judge reporting** [vendor]: J is reported as mean ± SD over 10 runs (SD ≈0.15–0.20 points). That SD reflects generation and judge randomness only, not question sampling — [arXiv 2504.19413](https://arxiv.org/abs/2504.19413)

### Inferences
- **Report chance-corrected agreement, not raw agreement.** CORTEX's judge validation reports Haiku-3 vs Sonnet agreement of 33–34/40 and judge self-disagreement of 5/40. With most answers graded correct, Thakur et al. show such numbers can sit beside low chance-corrected agreement and large score offsets. CORTEX should report Scott's π (or κ) and the mean score difference between judges, not just agreement counts.
- **The leniency fix needs negative controls.** CORTEX's judge was made more lenient ("never penalise true extras, unasked context, caveats"). The documented failure is leniency (P+ up to 0.99, dummy answers accepted). Add answers the judge must fail: an empty answer, "Yes", a fluent answer about the wrong project, and a plausible answer with one wrong key fact. Report the pass rate on these controls with every grading run.
- **Majority-of-3 per-fact grading is consistent with the literature.** Checklists improve consistency (CheckEval) and human agreement (TICK); repeated judging reduces self-inconsistency (Rating Roulette). Its residual 5/40 self-disagreement should be reported with each result, and the judge configuration must stay identical across arms (as CORTEX's harness does).
- **Paired differences are more trustworthy than absolute scores.** Judges rank systems far better than they score them (ρ 0.98–0.99 even for weak judges), so a statement like "v7 − v5 = −3.6" is better supported than "v7 = 0.792".
- **Calibrate with a small human set.** Hand-labelling about 150 answers once, ARES/PPI-style (about 1–2 hours for the one human), would give bias-corrected accuracy and a real judge-vs-human π. Without it, judge agreement is only judge-vs-judge.

### Gaps
- Zheng et al.'s exact position-consistency and verbosity-attack numbers were not retrieved (abstract only).
- A search summary mentioned a survey claiming ARES is "25.9% more accurate" than RAGAS; the survey was not identified or checked.
- G-Eval's correlation figures were not verified in this session.
- Rating Roulette's numeric reliability coefficients were not obtained.
- I found no head-to-head of per-fact vs holistic grading on memory QA with human labels.

## 7. Evaluation methodology: how many questions are needed to detect a given difference (power, paired tests, bootstrap)?

### Takeaway
Use paired per-question differences. The standard error is SE = √(Var(dᵢ)/n), and the minimum detectable effect at 80% power and α=0.05 is about 2.8 × SE. Miller's (Anthropic) worked example needs about 969 questions to detect a 3-point difference, hence his advice that evals "should contain at least 1,000 questions". Grouped questions need clustered standard errors, which can be over 3x the naive ones. Repeating runs (K) only shrinks the within-question part of the variance. On significance tests, a large IR simulation study recommends the paired t-test (or permutation test). It found the bootstrap-shift test biased towards small p-values at small sample sizes, and the Wilcoxon and sign tests unreliable.

### Cited Findings
- **Miller, "Adding Error Bars to Evals"** [Anthropic author, methodology paper; 1 Nov 2024]:
  - **Basic SE:** SE = √(Var(s)/n); for binary scores, √(p(1−p)/n). A bootstrap is "unnecessary unless a complicated sampling scheme or estimator is used".
  - **Clustered SEs:** needed when questions are grouped (shared passages or sources). Cluster-adjusted SEs were 3.05x (DROP), 1.10x (RACE-H) and 1.88x (MGSM) the naive ones — [arXiv 2411.00640](https://arxiv.org/abs/2411.00640)
- **Paired comparison** (Miller): SE_paired = √(SE_A² + SE_B² − 2·SE_A·SE_B·Corr(s_A, s_B)). Variance falls whenever the two systems agree on which questions are hard (with correlation 0.5, variance falls by a third). Recommendation: "use the paired version … wherever practicable", and report the pairwise difference, its SE and the score correlation — [arXiv 2411.00640](https://arxiv.org/abs/2411.00640)
- **Repeated sampling** (Miller): answering each question K times divides the within-question variance by K. Under uniform difficulty, Var(K)/Var(1) = (1 + 2/K)/3: K=2 cuts total variance by 1/3, K=4 by 1/2, K=6 by 5/9, and no K can cut it by more than 2/3. Pooling K×N answers as if independent is wrong. Lowering temperature to reduce variance is discouraged because it can shift the expected score — [arXiv 2411.00640](https://arxiv.org/abs/2411.00640)
- **Power and sample size** (Miller): n = (z_{α/2} + z_β)² · (ω² + σ_A²/K_A + σ_B²/K_B) / δ², where ω² = Var(x_A) + Var(x_B) − 2Cov(x_A, x_B). Worked examples:
  - ω² = 1/9, δ = 3 points, 80% power, α = .05 → n ≈ 969.
  - With n = 198, raising K from 1 to 10 lowers the minimum detectable effect from 13.2% to 7.5% — [arXiv 2411.00640](https://arxiv.org/abs/2411.00640)
- **Urbano, Lima & Hanjalic** [independent IR methodology; SIGIR 2019, outside the 2023–26 window but the standard reference]. Simulation on TREC data: over 500 million p-values across tests, measures, topic-set sizes and effect sizes.
  - The t-test and permutation test keep Type I error at α across measures, topic-set sizes and significance levels. They behave almost identically; the t-test is the "top recommendation" for simplicity and robustness to sample size.
  - The bootstrap-shift test "shows a systematic bias towards small p-values and is therefore more prone to Type I errors". Large samples reduce the bias, but they still propose discontinuing it.
  - The Wilcoxon and sign tests should be discontinued as unreliable.
  - Type III errors (right rejection, wrong direction) reach about 2% for small topic sets — [arXiv 1905.11096](https://arxiv.org/abs/1905.11096)

### Inferences
- **What CORTEX's 90-question held-out run can detect.** These are back-of-envelope figures from its reported CI, with ω² and K effects implicitly included.
  - **v7 − v5:** the paired CI [−.094, +.022] implies SE ≈ 0.030 and a minimum detectable effect of about 2.8 × 0.030 ≈ **8.3 points** at 80% power.
  - **Questions needed:** to detect the observed **3.6-point** gap at 80% power, n ≈ 90 × (8.3/3.6)² ≈ **480 questions**. A 5-point gap needs about **250**; a 10-point gap about **62**.
  - **Relational-graph comparison (60 questions):** CI [−.021, +.117] implies SE ≈ 0.035 and a minimum detectable effect of about 10 points. The pre-registered rule (point estimate ≥ +10 **and** CI excluding 0) therefore had only **about 50% power even if the true effect were exactly +10**. At the observed +4.6, the chance of the CI excluding 0 was about 25%. The verdict "fails the bar" is correct as a decision rule, but it is weak evidence that the graph does nothing.
- **Repeats help, but the gain is capped.** Going from K=2 to K=4 runs per question cuts variance by a further 25% under Miller's uniform-difficulty example (SE × 0.87, worth about 33% more questions). CORTEX's observation that 15/40 questions changed score between identical runs means within-question variance is large, so K=3–4 is cheap power. New questions are still the main lever.
- **Questions are clustered.** They come from 7 source transcripts and two question-writing agents. If outcomes correlate within source chat, the true SEs are larger than the per-question bootstrap shows (Miller saw up to 3x). CORTEX should compute a cluster bootstrap or clustered SE by source chat at least once, to see whether the CIs widen.
- **Cross-check the bootstrap.** CORTEX's paired bootstrap CI is a resampling method, so Urbano's warning about the bootstrap-shift test's anti-conservatism at small n applies in spirit. Report a paired t-test (or exact permutation test) beside it; at n=90 they should agree, and disagreement would be a red flag.
- **Pre-register at the minimum detectable effect.** Future bars should state the question count needed for the bar to have about 80% power, e.g. "graph must win by ≥10 points on ≥120 relational questions".

### Gaps
- I did not fetch Card et al. (2020, "With Little Power Comes Great Responsibility") or Sakai's topic-set-size design work.
- The per-question variance components (ω² vs σ²) for CORTEX's arms were not available to me, so the numbers above are back-calculated from the reported CIs and approximate.

## 8. Evaluation methodology: keeping held-out sets uncontaminated, and judge-free retrieval metrics

### Takeaway
- **Fresh sets matter.** Fresh, never-tuned-on question sets expose overfitting about as large as the effects memory papers report: up to 8 points on GSM1k vs GSM8k, with systematic overfitting across whole model families.
- **Judge-free retrieval metrics exist.** Recall@k and NDCG@k against gold evidence locations (LongMemEval) and per-document downstream utility (eRAG) are cheap, deterministic checks that avoid judge noise.
- **They transfer only partly.** In LongMemEval, +9.4% recall@k became only +5.4% final accuracy. eRAG's per-document utility labels track end-to-end performance better than relevance-label baselines (Kendall τ +0.168 to +0.494).

### Cited Findings
- **GSM1k** [independent; Zhang et al.; May 2024, v4 Nov 2024]: a newly written set that mirrors GSM8k on human solve rate, solution steps and answer magnitude. Leading LLMs drop by up to 8% on it, and several model families show systematic overfitting across almost all sizes. A model's probability of generating GSM8k examples correlates with its GSM8k–GSM1k gap (Spearman r² = 0.36) — [arXiv 2405.00332](https://arxiv.org/abs/2405.00332)
- **LongMemEval retrieval metrics** [independent]: retrieval is scored judge-free with Recall@k and NDCG@k against human-annotated answer locations (evidence sessions or rounds).
  - Fact-augmented key expansion: +9.4% recall@k and +5.4% final accuracy on average.
  - Time-aware query expansion: +11.3% (rounds) and +6.8% (sessions) temporal-reasoning recall with a GPT-4o query expander.
  - Chain-of-Note and structured reading: up to about +10 absolute QA points.
  - Long-context readers given the whole LongMemEval_S history score 30–60% lower than when given only the oracle evidence (GPT-4o −30.3%; Llama 3.1 70B −55.1%) — [arXiv 2410.10813](https://arxiv.org/abs/2410.10813)
- **eRAG** [independent; Salemi & Zamani; Apr 2024; the arXiv page lists no venue]: each retrieved document is fed alone to the RAG system's LLM and scored against the task's ground truth, giving a per-document utility label that is then aggregated with ranking metrics. Kendall τ correlation with end-to-end RAG performance improves 0.168–0.494 over baselines, using up to 50x less GPU memory than end-to-end evaluation — [arXiv 2404.13781](https://arxiv.org/abs/2404.13781)
- **Benchmark-validity critiques from vendors:** Letta says memory benchmarks "may not be very meaningful" and that LoCoMo's AI-generated two-speaker conversations measure long-conversation retrieval, not agentic memory — [Letta blog](https://www.letta.com/blog/benchmarking-ai-agent-memory). Zep argues LoCoMo is flawed and prefers LongMemEval — [Zep blog](https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)
- **Internal inconsistencies in widely used memory papers** [flagged by the fetch tool's extraction pass; not independently confirmed against the PDFs]:
  - LoCoMo: GPT-4-turbo overall F1 is 32.1 in the table vs 32.4 in the text.
  - Zep: top-10 vs top-20 retrieved items, and a duplicated per-type row.
  - Miller's fictional example: a HumanEval value of 86.7 vs 87.7.

  Benchmark tables need checking before reuse — [arXiv 2402.17753](https://arxiv.org/abs/2402.17753); [arXiv 2501.13956](https://arxiv.org/abs/2501.13956); [arXiv 2411.00640](https://arxiv.org/abs/2411.00640)

### Inferences
- **The held-out set is now partly spent.** CORTEX's rule (only before/after totals on the held-out set, no per-question failure analysis) is the right discipline; it is the reusable-holdout idea in practice. The 90-question set has been used once for a before/after decision, though. Each further tuning-and-retest cycle on it adds adaptive overfitting of unknown size, and GSM1k shows such effects reach about 8 points, more than the gaps CORTEX is trying to resolve. The synthetic corpus, and questions written only from chats after a freeze date (a time split), are the clean next sets.
- **Retrieval-to-accuracy transfer.** CORTEX's judge-free retrieval metric (`retrieval_eval.py`, ref recall of search plus injection pack) is the LongMemEval-style check. Its own transfer ratio, relational ref recall .38 → .48 (+10) vs relational accuracy .738 → .771 (+3.3), is about 0.3. Store and rules changed at the same time, so this is a rough number. It is lower than LongMemEval's 9.4 → 5.4 (about 0.57) and suggests the reader's use of what was retrieved, not retrieval alone, is now the larger bottleneck. Section 1's evidence that agents with good search tools do well points the same way.
- **An eRAG-style check for CORTEX:** for a sample of questions, give the answering model only one record (or one session-log span) at a time and score with the existing judge. This shows which stored records are useful, and is better aligned with end accuracy than "was the gold source retrieved".
- **Contamination paths specific to CORTEX:**
  - The question writers saw the transcripts, and the extraction model reads the same transcripts. That is legitimate, but the builder must not read expected answers (already a rule).
  - The judge must never see system internals.
  - Prompts or extraction guides tuned on dev failures should be frozen before a held-out run.

### Gaps
- LiveBench-style rolling question sets and formal adaptive-data-analysis methods (reusable holdout or thresholdout) were not researched in this session.
- Whether LoCoMo's released QA carries gold evidence IDs usable for recall@k was not verified here.
- I found no study measuring how much repeated before/after use of one memory-QA held-out set inflates results.

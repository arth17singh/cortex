# Long-term conversational and agent memory benchmarks (2023–2026): what they measure, what their ablations show, and how far to trust the numbers

Compiled 2026-11-04. Tags: **[IND]** = independent academic result. **[VEN]** = vendor or vendor-adjacent: the author builds a memory product that appears in the comparison. Retrieval dependency: **[LEX]** = shown with BM25 or grep, or needs no embeddings. **[DENSE]** = shown only with an embedding retriever. **[LLM]** = needs a model call at index or query time (no embeddings, but not stdlib-only). "(search summary)" means the figure comes from a search-result summary of the page, not from a page I fetched.

## 1. LongMemEval (Wu et al., arXiv 2410.10813, Oct 2024): the abilities it tests and its design findings

### Takeaway
On 500 questions over chat histories of about 115k tokens (S) and 1.5M tokens (M), reading the whole history scores 30–60% below reading only the evidence. The ablations favour raw rounds or sessions as the stored value with extracted facts appended to each item's index key (+9.4% recall and +5.4% QA on average, and +4.9 to +8.2 Recall@5 points for BM25 too), a time range inferred by an LLM for temporal questions (+6.8–11.3% recall), and Chain-of-Note with JSON for reading (up to about 10 points); with raw keys BM25 trails dense retrievers by 9–19 Recall@5 points, and the time-aware and key-merging results exist only for the dense Stella V5 retriever.

### Cited Findings
**What it tests**
- Five abilities: information extraction, multi-session reasoning, knowledge updates, temporal reasoning and abstention. Seven question types: single-session-user, single-session-assistant, single-session-preference, multi-session, knowledge-update, temporal-reasoning and abstention. 500 hand-written questions [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- LongMemEval_S is about 115k tokens per question (about 50 sessions). LongMemEval_M is 500 sessions, about 1.5M tokens [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Abstention: 30 questions taken from the other types and rewritten with a false premise. The right answer is "I don't know" [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Filler ("haystack") sessions are 25% ShareGPT, 25% UltraChat and 50% simulated. The paper does not discuss training-data contamination [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Grading uses a GPT-4o judge with "more than 97% agreement with human experts", checked on 30 sampled questions per question type [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)

**How much accuracy drops**
- Commercial assistants (Fig. 3a): offline reading with GPT-4o 0.918. ChatGPT (GPT-4o) 0.577 (−37%). ChatGPT (GPT-4o-mini) 0.711. Coze (GPT-4o) 0.330 (−64%). Coze (GPT-3.5-turbo) 0.247 [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Long-context LLMs, evidence only ("oracle") vs the full LongMemEval_S history, direct reading (Fig. 3b):

  | Model | Evidence only | Full history | Drop |
  |---|---|---|---|
  | GPT-4o | 0.870 | 0.606 | −30.3% |
  | Llama 3.1 70B | 0.744 | 0.334 | −55.1% |
  | Llama 3.1 8B | 0.710 | 0.454 | −36.1% |
  | Phi-3 14B | 0.702 | 0.380 | −45.9% |
  | Phi-3.5-mini | 0.660 | 0.342 | −48.1% |

  [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- The same comparison with Chain-of-Note: GPT-4o 0.924 → 0.640. Llama 3.1 70B 0.848 → 0.286. Llama 3.1 8B 0.710 → 0.420. Phi-3 14B 0.722 → 0.344. Phi-3.5-mini 0.652 → 0.324 [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Error analysis (App. E.5): a correct answer needs correct retrieval about 90% of the time. Cases where retrieval was right but the answer was wrong are 15–19% of all instances, which is 40–50% of the errors [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)

**Retrievers compared (App. Table 9)**

| Retriever | Recall@5 sessions | Recall@5 rounds | NDCG@5 sessions | NDCG@5 rounds | Recall@10 sessions | Recall@10 rounds |
|---|---|---|---|---|---|---|
| BM25 | 0.634 | 0.472 | 0.516 | 0.352 | 0.710 | 0.538 |
| Contriever | 0.723 | 0.589 | 0.634 | 0.454 | 0.823 | 0.747 |
| Stella V5 1.5B | 0.720 | 0.660 | 0.594 | 0.498 | 0.794 | 0.784 |

All rows use the raw text as the key (K=V) [IND][LEX for the BM25 row] — [LongMemEval](https://arxiv.org/html/2410.10813)
- gte-Qwen2-7B is not reported: "We do not report the results of retrievers that use larger embedding models." The main experiments use "dense retrieval with the 1.5B Stella V5 model" [IND][DENSE] — [LongMemEval](https://arxiv.org/html/2410.10813)

**Session decomposition (storing rounds instead of whole sessions)**
- Sec. 5.2 and Fig. 5: splitting sessions into rounds "significantly improves" reading with GPT-4o, and performs about the same as sessions with Llama 3.1 8B [IND][DENSE] — [LongMemEval](https://arxiv.org/html/2410.10813)
- LongMemEval_M with Stella (Tables 3 and 10): Recall@5 at K=V is 0.582 for rounds and 0.706 for sessions; the units differ, so these two aren't directly comparable. GPT-4o QA accuracy:

  | Stored unit and key | Top-5 | Top-10 |
  |---|---|---|
  | Rounds, K=V | 0.615 | 0.670 |
  | Rounds, K=V+fact | 0.657 | 0.720 |
  | Sessions, K=V | 0.670 | 0.676 |
  | Sessions, K=V+fact | 0.714 | 0.700 |

  [IND][DENSE] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Indexing by a summary or by facts alone, without the raw text, lowers recall: session Recall@5 0.706 (K=V) vs 0.572 (K=summary); round Recall@5 0.582 (K=V) vs 0.530 (K=fact) [IND][DENSE] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Replacing what the reader sees (the stored value) with summaries or facts lowers QA "due to information loss", per the paper's text. The exception is multi-session reasoning, where fact decomposition consistently helps. The QA values for this comparison were not captured [IND][DENSE] — [LongMemEval](https://arxiv.org/html/2410.10813)

**Fact-augmented key expansion (indexing each item under its own text plus facts extracted from it)**
- Averaged across reader models: +9.4% recall@k and +5.4% final accuracy (Table 3, LongMemEval_M). Rounds: Recall@5 0.582 → 0.644, GPT-4o top-5 0.615 → 0.657. Sessions: Recall@5 0.706 → 0.732, GPT-4o top-5 0.670 → 0.714 [IND][DENSE][LLM extraction] — [LongMemEval](https://arxiv.org/html/2410.10813)
- With BM25 (Table 9): sessions Recall@5 0.634 → 0.683, Recall@10 0.710 → 0.757, NDCG@5 0.516 → 0.560. Rounds Recall@5 0.472 → 0.554, Recall@10 0.538 → 0.608, NDCG@5 0.352 → 0.454 [IND][LEX at query time; LLM at index time] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Other expansions with BM25: keyphrases don't help (Recall@5 0.632 on sessions, 0.453 on rounds). Summaries (tested on sessions only) give Recall@5 0.626 but NDCG@5 0.544. The appendix says fact expansion "consistently improves the performance over directly using the value as the key" and "expanding the key with facts still gives the greatest performance gain" [IND][LEX] — [LongMemEval](https://arxiv.org/html/2410.10813)
- How the facts are attached matters (Table 10, Stella, rounds). "Key merging" appends the facts to the item's own key: Recall@5 0.644, GPT-4o top-10 0.720. "Rank merging" indexes each fact as a separate key pointing to the item and merges the rankings: Recall@5 0.478, below the K=V baseline of 0.582, and GPT-4o top-10 0.596. Rank merging with keyphrases: Recall@5 0.386. The authors suggest the cause is that rank merging makes the index (m+1) times larger [IND][DENSE] — [LongMemEval](https://arxiv.org/html/2410.10813)
- The tables disagree with each other. Table 9's Stella K=V values (0.720 / 0.660) differ from Table 3's (0.706 / 0.582). Table 9 doesn't name its dataset in the text I read. One Stella NDCG@5 value (0.520, sessions, K=V+fact) disagrees with Table 10 [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)

**Time-aware query expansion (timestamped facts at index time, plus a time range inferred by an LLM at query time to narrow the search)**
- On the temporal-reasoning subset (Table 4), with GPT-4o extracting the time range: average +11.3% recall with rounds and +6.8% with sessions. Recall@5 examples: rounds K=V 0.421 → 0.451; rounds K=V+fact 0.489 → 0.526; sessions K=V 0.639 → 0.654; sessions K=V+fact 0.684 → 0.722 [IND][DENSE][LLM] — [LongMemEval](https://arxiv.org/html/2410.10813)
- With Llama 3.1 8B extracting the time range, the method "fails to help consistently". No BM25 run is reported [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)

**Reading strategies**
- Chain-of-Note (write notes from each retrieved item before answering) with retrieved items formatted as JSON: up to about 10 absolute points over the worst setting, across three LLMs (Fig. 6; the values are only in the figure) [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- App. Table 8: Chain-of-Note and fact-key expansion "consistently improve" results for five more small models (Mistral-Nemo, Qwen2.5-7B, Phi-3.5-mini, Llama-3.2-3B, Llama-3.2-1B) [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)

### Inferences
- The paper separates two uses of extracted facts, and the difference matters for a records-first design. Indexing by facts alone, without the raw text, lowers recall. Showing the reader facts instead of the raw text lowers QA, except on multi-session questions. Appending facts to the raw item's key helps on both counts.
- The only expansion shown to help BM25 keeps the raw text as the value and appends the extracted facts to that item's index text. Its gain is largest on turn-sized items (+8.2 Recall@5), where BM25 is weakest; short documents gain vocabulary. Indexing facts as separate documents (rank merging) did much worse with dense retrieval. It wasn't tested with BM25, but the same mechanism (many small keys competing with each other) would apply to lexical search.
- BM25's deficit is mostly about item size. It is 18.8 Recall@5 points behind Stella on rounds and 8.6 behind on sessions. Once session keys carry facts, the gap is 3.7 (0.683 vs Stella K=V 0.720). BM25 does better with bigger items. A stdlib-friendly compromise is to match on small units and return the parent unit, as in the Emergence design in section 4.
- Time-aware expansion has two parts. The date filter costs nothing once dates are stored. Extracting the time range from the query needed GPT-4o; an 8B model failed. A rule-based date parser is plausible but unmeasured.
- Chain-of-Note helps when the reader sees a small, relevant set (GPT-4o with evidence only: 0.870 → 0.924). It doesn't help open models read the whole history (Llama 70B on S: 0.334 → 0.286). Structured note-taking belongs on top of retrieval; it doesn't fix long contexts.
- About half the errors happen after retrieval was already correct. Reading instructions deserve as much tuning as ranking.

### Gaps
- The Fig. 5 values (rounds vs sessions at matched token budgets) and Fig. 6 values (reading strategies) are only in images. Per-question-type breakdowns were not captured.
- The text I read doesn't say whether "+9.4% / +5.4%" and "+11.3% / +6.8%" are relative or absolute. The Recall@5 examples suggest relative.
- Time-aware expansion and the key-vs-rank merging comparison have no BM25 numbers.
- The commercial-assistant test used a smaller subset run by hand. Its size was not captured.
- The venue is widely cited as ICLR 2025; I did not confirm it on the pages read. I found no official LongMemEval follow-up version. Later use of the benchmark comes through MemoryAgentBench's LME(S*) variant and vendor leaderboards (sections 3 and 4).

## 2. LoCoMo (Maharana et al., arXiv 2402.17753, Feb 2024): question categories, baseline results and known problems

### Takeaway
LoCoMo (50 LLM-generated, human-edited conversations of about 300 turns in the paper; everyone reports on a 10-conversation public release with 1,540 scored and 446 adversarial questions) found in 2024 that long context and dense RAG stayed far below humans (best about 41 F1 vs 87.9), that extracted "observations" beat raw turns and session summaries as retrieval units at small top-k, and that longer context made adversarial (unanswerable) questions worse. Since 2025 its known problems are that the public set fits in a context window (so full context beats memory systems), about 6.4% of the answer key is wrong, the adversarial category is usually dropped, and the vendors' LLM judge accepts most vague wrong answers.

### Cited Findings
- Dataset as described in the paper: 50 conversations averaging 304.9 turns, 19.3 sessions (up to 35) and 9,209 tokens. Two gpt-3.5-turbo agents with personas and temporal event graphs generated them. Annotators edited about 15% of turns and removed or replaced about 19% of images [IND] — [LoCoMo](https://arxiv.org/html/2402.17753)
- Question categories (paper, Table 5): single-hop 2,705 (36%), multi-hop 1,104 (14.6%), temporal 1,547 (20.6%), open-domain 285 (3.9%), adversarial 1,871 (24.9%); 7,512 in total. Adversarial questions are "designed to trick the agent into providing wrong answers", and the agent should recognise them as unanswerable [IND] — [LoCoMo](https://arxiv.org/html/2402.17753)
- Metric: token F1. The paper describes it both as "F1 score for exact matches" and as "F1 partial match" [IND] — [LoCoMo](https://arxiv.org/html/2402.17753)
- Public release `locomo10.json`: 10 conversations, 1,540 scored questions plus 446 adversarial ones (22.5%). Category sizes range from 96 (open-domain) to 841 [VEN-adjacent] — [locomo-audit](https://github.com/dial481/locomo-audit)
- The public conversations run about 16k–26k tokens [VEN] — [Zep](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/). Mem0's full-context baseline uses 26,031 tokens [VEN] — [Mem0 paper](https://arxiv.org/html/2504.19413)
- Long-context baselines (Table 2, overall F1): human 87.9 (single-hop 95.1, multi-hop 85.8, temporal 92.6, open-domain 75.4, adversarial 89.4). Mistral-7B 13.9. Llama-2-70B 17.9. GPT-3.5-turbo (4K context) 22.4. GPT-4-turbo (4K) 32.1, with temporal 10.4 and adversarial 70.2. GPT-3.5-turbo-16K at 4K / 8K / 12K / 16K context: 24.1 / 25.2 / 33.5 / 37.8, while its adversarial F1 falls 13.1 / 8.4 / 6.4 / 2.1 [IND] — [LoCoMo](https://arxiv.org/html/2402.17753)
- RAG (Table 3; DRAGON dense retriever, gpt-3.5-turbo-16k reader; overall F1, with retrieval recall R@k):

  | What is retrieved | Overall F1 at top-k | Evidence recall |
  |---|---|---|
  | Nothing | 22.4 | – |
  | Raw dialog turns | top-5 31.7, top-10 34.6, top-25 35.8, top-50 34.8 | top-5 58.8, top-50 84.8 |
  | Observations | top-5 41.4, top-10 38.8, top-25 38.0, top-50 37.8 | top-5 49.6, top-50 71.1 |
  | Session summaries | top-2 29.9, top-5 32.5, top-10 31.5 | top-2 61.5, top-10 90.7 |

  [IND][DENSE] — [LoCoMo](https://arxiv.org/html/2402.17753)
- The paper's conclusions: long context and RAG improve on the base model by 22–66% but still trail humans by 56% overall and by 73% on temporal questions. The best temporal score is 41.9 (observations, top-5) against 92.6 for humans. Long contexts make models hallucinate on adversarial questions. Long context does not improve event summarisation [IND] — [LoCoMo](https://arxiv.org/html/2402.17753)
- Problems raised by Zep (May 2025) [VEN] — [Zep](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/):
  - category 5 can't be used because its ground-truth answers are missing;
  - some image questions can't be answered from the BLIP captions;
  - some questions attribute statements to the wrong speaker;
  - some questions are ambiguous, with several right answers;
  - there are no knowledge-update questions;
  - the conversations fit in modern context windows, and full context (about 73%) beat Mem0's best (about 68%).
- Audit (2026): 99 of 1,540 golden answers are wrong (6.4%), which caps the achievable score at 93.57%. A multiple-choice fix for category 5 exists but "has never been implemented" [VEN-adjacent] — [locomo-audit](https://github.com/dial481/locomo-audit). The audit also counts 57 issues that affect only the evidence citations (search summary) — [Penfield Labs write-up](https://dev.to/penfieldlabs/we-audited-locomo-64-of-the-answer-key-is-wrong-and-the-judge-accepts-up-to-63-of-intentionally-33lg)

### Inferences
- In 2024, with a weak reader and a small top-k, extracted observations were the better unit to retrieve. They gave higher QA F1 than raw turns at every k (41.4 vs 31.7 at top-5), despite lower evidence recall (49.6 vs 58.8): denser items fit more answer-bearing content into a small budget. This evidence comes from a dense retriever (DRAGON). Later results with stronger readers reverse it: full context scores 72.9–92.6 (section 4).
- Session summaries had the highest recall and the lowest QA. This agrees with LongMemEval that summaries lose the details questions ask about.
- The public set fits in about 26k tokens, so LoCoMo mainly measures the reader and the answer prompt, not retrieval at scale. It says little about histories larger than the context window, which is the situation a coding agent is in.
- Most vendor "LoCoMo J" numbers exclude the adversarial category. They therefore don't measure abstention, which a memory system needs in order to say "not recorded".

### Gaps
- LoCoMo has no BM25 or other lexical baseline.
- I did not re-quote the paper's exact definition of "observations" (statements generated about each speaker per session).
- There are reports that the released JSON numbers its categories in a different order from the paper, which has led to mislabelled per-category results. I did not verify them.
- I found no independent replication of the audit's 6.4% figure.

## 3. Newer benchmarks (2025–2026), including ones for coding agents

### Takeaway
The newer independent benchmarks (MemoryAgentBench, HaluMem, BEAM, MemBench) add test-time learning, long-range understanding, forgetting, extraction and update errors, and histories up to 10M tokens. They find that no design wins every ability, that plain BM25 over raw 512-token chunks matches embedding RAG and scores about double the fact-extraction products on MemoryAgentBench (the only one of them that tests BM25), that extraction pipelines drop most facts (HaluMem), and that facts which were later updated or contradicted are the least-solved ability. For coding agents I found no independent benchmark with published numbers on memory across coding sessions: MEMTRACK (workplace tools including Git; GPT-5 reaches 60%) is the closest, and SWE-Bench-CL, LoCoBench-Agent and LongMemCode gave no memory-specific results.

### Cited Findings
**MemoryAgentBench** (Hu, Wang, McAuley, UC San Diego; arXiv 2507.05257, Jul 2025, v4 Jun 2026; ICLR 2026 according to a secondary summary)
- Four abilities and their datasets [IND] — [MemoryAgentBench](https://arxiv.org/html/2507.05257); [secondary summary](https://www.emergentmind.com/topics/memoryagentbench):
  - Accurate Retrieval (AR): SH-Doc QA, MH-Doc QA, LongMemEval S*, and the new EventQA;
  - Test-Time Learning (TTL): BANKING77, CLINC150, NLU, TREC Coarse and Fine, movie recommendation;
  - Long-Range Understanding (LRU): ∞Bench-Sum, DetectiveQA;
  - Selective Forgetting (SF): the new FactConsolidation-SH and -MH (called "conflict resolution" in earlier versions).
- Overall scores (Table 3):

  | Kind | System | Overall |
  |---|---|---|
  | Long-context | GPT-5-mini | 60.6 |
  | Long-context | GPT-4o | 48.8 |
  | Long-context | GPT-4o-mini | 42.2 |
  | Lexical RAG | BM25 (AR 60.5, TTL 44.5, LRU 35.6, SF 25.5) | 41.5 |
  | Embedding RAG | Qwen3-Embedding-4B | 38.2 |
  | Embedding RAG | text-embedding-3-large | 38.0 |
  | Embedding RAG | Contriever | 29.8 |
  | Structured RAG | HippoRAG-v2 | 41.6 |
  | Structured RAG | MemoRAG | 30.9 |
  | Structured RAG | RAPTOR | 27.0 |
  | Structured RAG | GraphRAG | 23.4 |
  | Memory product | Zep | 24.0 |
  | Memory product | Mem0 | 21.1 |
  | Memory product | Cognee | 20.6 |
  | Agentic memory | MemGPT | 28.3 |
  | Agentic memory | MIRIX (37.7 on GPT-4.1-mini) | 26.2 |
  | Agentic memory | Self-RAG | 18.7 |

  [IND][LEX for BM25] — [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- Accurate-retrieval datasets:

  | System | SH-QA | MH-QA | LME(S*) | EventQA |
  |---|---|---|---|---|
  | BM25 | 66.0 | 56.0 | 45.3 | 74.6 |
  | Contriever | 22.0 | 31.0 | 15.7 | 66.8 |
  | text-embedding-3-small | 60.0 | 44.0 | 48.3 | 63.0 |
  | text-embedding-3-large | 54.0 | 44.0 | 50.3 | 70.0 |
  | Qwen3-Embedding-4B | 57.0 | 47.0 | 43.3 | 71.4 |
  | HippoRAG-v2 | 76.0 | 66.0 | 50.7 | 67.6 |
  | Mem0 | 25.0 | 32.0 | 36.0 | 37.5 |
  | Zep | 44.0 | 25.0 | 38.3 | 42.5 |
  | Cognee | 31.0 | 26.0 | 29.3 | 26.8 |
  | MemGPT | 41.0 | 38.0 | 32.0 | 26.2 |
  | GPT-4o-mini, 128K context | 64.0 | 43.0 | 30.7 | 59.0 |
  | GPT-4o, 128K context | 72.0 | 51.0 | 32.0 | 77.2 |
  | GPT-5-mini, 400K context | 85.0 | 71.0 | 63.3 | 78.2 |

  [IND] — [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- Setup: 512-token chunks for the accurate-retrieval and forgetting tasks, 4,096 elsewhere. Mem0, Cognee, Zep and MIRIX always use 4,096. Top-10 chunks are retrieved [IND] — [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- Selective forgetting: BM25 scores 48.0 on FC-SH and 3.0 on FC-MH; GPT-5-mini scores 78.0 and 28.0. Every method scores "at most 28%" on multi-hop. o4-mini scores 80.0 on FC-MH at 6K tokens but 14.0 at 32K [IND] — [MemoryAgentBench](https://arxiv.org/html/2507.05257). An earlier version reported every method at or below 7% on multi-hop, and GPT-4o memory agents at about 60% on single-hop (search summary) — [Cognee guide](https://www.cognee.ai/agent-memory-evaluation-datasets-benchmarks)
- The paper's conclusions: RAG agents "excel at extracting a small snippet of text" and mostly beat their backbone model on accurate retrieval. Long-context models do best on test-time learning and long-range understanding. RAG is "inherently less suited" to tasks that need a large, coherent context, and larger chunks hurt long-range understanding [IND] — [MemoryAgentBench](https://arxiv.org/html/2507.05257)

**HaluMem** (Chen et al.; arXiv 2511.03506, Nov 2025, v3 Jan 2026)
- Scores each memory operation separately (extraction, updating, question answering) instead of only end-to-end QA. HaluMem-Medium and HaluMem-Long each have about 15k memory points and 3.5k questions, with about 1.5k and 2.6k turns per user respectively, and contexts over 1M tokens [IND] — [HaluMem](https://arxiv.org/abs/2511.03506). Medium has 30,073 turns from 20 users (search summary) — [TRUSTMEM](https://arxiv.org/pdf/2606.25161)
- Results (Table 3):

  | System | Medium: extraction recall | Medium: update correct (omitted) | Medium: QA correct | Long: extraction recall | Long: QA correct |
  |---|---|---|---|---|---|
  | Mem0 | 42.91% | 25.50% (74.02%) | 53.02% | 3.23% | 28.11% |
  | Mem0-Graph | 43.28% | 24.50% (75.24%) | 54.66% | 2.24% | 32.44% |
  | Memobase | 14.55% | 5.20% (94.25%) | 35.33% | 6.18% | 33.60% |
  | Supermemory | 41.53% | 16.37% (82.47%) | 54.07% | 53.02% | 53.77% |
  | Zep | not scored | 47.28% (52.31%) | 55.47% | not scored | 50.19% |
  | MemOS | 74.07% | 62.11% (37.48%) | 67.23% | 81.90% | 64.44% |

  On Long, Mem0 got 1.45% of updates right and omitted 98.51%. Zep has no extraction scores because it has no API that returns the extracted memories [IND] — [HaluMem](https://arxiv.org/html/2511.03506)
- The paper's summary: except for MemOS, every system recalls under 60% of memory points. All have accuracy under 62%. Most omit over 50% of updates. Update hallucination is under 2%, but few samples reach the update step. All answer under 70% of questions correctly. Hallucinations made during extraction and updating carry through into the answers [IND] — [HaluMem](https://arxiv.org/html/2511.03506)

**BEAM** ("Beyond a Million Tokens", Tavakoli et al.; arXiv 2510.27246, Oct 2025, v2 Feb 2026)
- 100 generated conversations and 2,000 validated questions, at lengths up to 10M tokens. "Even LLMs with 1M token context windows (with and without retrieval-augmentation) struggle as dialogues lengthen." The proposed method, LIGHT, combines a long-term episodic memory, a short-term working memory and a scratchpad of salient facts. It gains 3.5–12.69% over the strongest baselines, and the ablation shows each part contributes [IND] — [BEAM](https://arxiv.org/abs/2510.27246)
- Vendor-reported BEAM figures: contradiction resolution about 0.357 at 1M tokens and 0.325 at 10M (search summary) [VEN] — [Cognee guide](https://www.cognee.ai/agent-memory-evaluation-datasets-benchmarks). Mem0 claims a 70.1% pass rate and a 0.641 average score on BEAM 1M, and warns that the often-quoted 64.1 is the average score, not the pass rate (search summary) [VEN] — [Mem0](https://mem0.ai/library/agent-memory/how-to-read-memory-benchmarks)

**MemBench** (Tan et al.; arXiv 2506.21605, Jun 2025; ACL 2025 Findings)
- Tests factual vs reflective memory in "participation" and "observation" scenarios, scored on effectiveness, efficiency and capacity. Headline numbers were not captured [IND] — [MemBench](https://arxiv.org/abs/2506.21605)

**Task-based benchmarks, 2026**
- DolphinBench (Rathi, Yadav, Singh; arXiv 2609.24971, Sep 2026): scores memory by whether tasks get done, and requires cost and latency to be reported with every result. Three knowledge-work personas, each with about 500k tokens of user messages and 200 tasks. Each task was checked to succeed only when the agent has the history. Results not captured — [DolphinBench](https://arxiv.org/abs/2609.24971)
- StreamMemBench (arXiv 2606.14571, Jun 2026): "Streaming Evaluation of Agent Memory for Future-Oriented Assistance". I have only the title — [StreamMemBench](https://arxiv.org/pdf/2606.14571)

**Coding agents and software projects**
- MEMTRACK (Patronus AI; arXiv 2510.01353, Oct 2025; listed at NeurIPS 2025): tracks memory and state across Slack, Linear, Git and codebase exploration, testing acquisition, selection and conflict resolution. Scored on correctness, efficiency and redundancy over 5 runs. The best model, GPT-5, reaches 60% correctness (search summary) — [MEMTRACK](https://www.arxiv.org/pdf/2510.01353); [NeurIPS listing](https://neurips.cc/virtual/2025/124523). It has 47 curated instances, according to a third-party review — [Liner review](https://liner.com/review/memtrack-evaluating-longterm-memory-and-state-tracking-in-multiplatform-dynamic)
- SWE-Bench-CL (Joshi, Chowdhury, Uysal; arXiv 2507.00014, Jun 2025): orders SWE-Bench Verified issues chronologically. Metrics: accuracy, forgetting, forward and backward transfer, tool-use efficiency, and composite continual-learning scores. Uses a FAISS semantic memory. The abstract gives no numbers comparing agents with and without memory [IND][DENSE] — [SWE-Bench-CL](https://arxiv.org/abs/2507.00014)
- LoCoBench-Agent (Salesforce AI Research; arXiv 2511.13998, Nov 2025): 8,000 interactive software-engineering scenarios on codebases of 10K–1M tokens. Memory management is one of the dimensions it scores. I found no memory-specific scores (search summary) — [LoCoBench-Agent](https://arxiv.org/pdf/2511.13998)
- LongMemCode (ArgosBrain team; Apr 2026 per search summary) [VEN]: 40 corpora and 14,228 scenarios. The headline corpus, kubernetes-2k, has 1,456 scenarios over about 14k Go files. Task mix: completion 32%, bug fix 22%, API discovery 14%, refactor 12%, test generation 10%, feature addition 10%. It scores retrieval quality, speed, compression and cost without an LLM. An `rg` wrapper "sets the floor". The Mem0 and Zep adapters are stubs, and the README shows no results — [LongMemCode](https://github.com/CataDef/LongMemCode)
- agentmemory [VEN]: an in-house benchmark of 15 fictional Claude Code sessions, which the project itself calls small (search summary) — [agentmemory comparison](https://cdn.jsdelivr.net/gh/rohitg00/agentmemory@0.9.27/benchmark/COMPARISON.md)

### Inferences
- MemoryAgentBench is the strongest independent support for BM25 as the default in a stdlib system. Over raw 512-token chunks it matches or beats off-the-shelf embedding RAG overall (41.5 vs 38.0–38.2) and scores about twice what Mem0 (21.1) and Zep (24.0) score. On LongMemEval-style chat retrieval it is a few points below OpenAI embeddings (45.3 vs 48.3–50.3). That fits LongMemEval's own finding that BM25 is weaker on conversational turns.
- The weak spot across benchmarks is knowing what is true after something changed: multi-hop forgetting in MemoryAgentBench is at most 28% (BM25 3.0), most systems in HaluMem omit over 50% of updates, and BEAM contradiction resolution is about 0.33 (vendor figure). None of these benchmarks tests a system with explicit supersession links, so whether such links fix the problem is unknown.
- HaluMem puts a number on the risk of storing only extracted facts. Even the best pipeline (MemOS, recall 74–82%) missed 18–26% of memory points; Mem0 missed 57% on Medium and 97% on Long. Anything the extractor drops can't be found later unless the raw source stays searchable.
- Possible conflicts of interest. This is from my own knowledge, not shown on the pages read, and unverified: HaluMem's author list overlaps with the MemOS team, and MemOS tops its tables. DolphinBench's second and third authors share names with Mem0's founders.
- Memory evaluation for coding agents is immature. No independent benchmark asks whether an agent remembers a past decision or a rejected option across coding sessions, so project-specific question sets are still the only direct measure.

### Gaps
- Not captured: BEAM's list of abilities and its per-model numbers; MemBench's datasets and results; any results in the body of SWE-Bench-CL; LoCoBench-Agent's memory scores; MEMTRACK's per-model table; DolphinBench and StreamMemBench results.
- MemoryAgentBench's LME(S*) is built differently from LongMemEval_S: GPT-4o with long context scores 32.0 there vs 60.6 in the LongMemEval paper. How it differs was not captured.
- Not researched: Letta's Context-Bench and Letta Memory Benchmark; ReasoningBank and Agent Workflow Memory (procedural memory on SWE-bench and WebArena); PersonaMem, DialSim, MSC/DMR.
- A May 2026 community benchmark on whether code edits respect earlier architectural decisions appeared in search results. It is unvalidated and I did not read it.

## 4. Leaderboards and replications: raw turns vs extracted facts, and BM25 vs dense retrieval

### Takeaway
Independent results agree that extracted facts help as an index over raw text but not as a replacement for it: fact-extraction products score about half of plain BM25 RAG on MemoryAgentBench and lose most facts on HaluMem, and LongMemEval improves only when facts are added to the raw items. Vendor numbers agree on LoCoMo (full context and agentic search over the raw file both beat Mem0), while on the longer LongMemEval_S an extraction system (Zep, 71.2%) beats full context (60.2%) and well-tuned RAG over raw turns beats both (82.4–86%); BM25 trails dense retrievers on turn-level chat recall in LongMemEval but leads them overall on MemoryAgentBench, and no vendor leaderboard reports BM25.

### Cited Findings
**Raw vs extracted on LoCoMo (public 10 conversations, J score, adversarial excluded)**
- Mem0 paper (Apr 28, 2025; gpt-4o-mini; the judge is "a separate, more capable LLM", not named; mean ± SD over 10 runs) [VEN][DENSE for the RAG rows] — [Mem0 paper](https://arxiv.org/html/2504.19413):

  | System | J score | Notes |
  |---|---|---|
  | Full context | 72.90 ± 0.19 | 26,031 tokens; total latency p50 9.870 s, p95 17.117 s |
  | Mem0 graph (Mem0g) | 68.44 | |
  | Mem0 | 66.88 | 1,764 tokens; p95 1.440 s |
  | Zep (as run by Mem0) | 65.99 | |
  | Best RAG | 60.97 | 256-token chunks, k=2, OpenAI text-embedding-3-small; 36.84–60.97 across chunk sizes 128–8,192 and k = 1–2 |
  | LangMem | 58.10 | |
  | OpenAI memory | 52.90 | |
  | A-Mem | 48.38 | |

- Zep (May 6, 2025): Zep scores 75.14 ± 0.17 when configured correctly [VEN] — [Zep](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)
- Letta (Aug 12, 2025): the whole conversation attached as one file, with tools grep, search_files (embedding search), open, close and answer_question. GPT-4o mini was forced to search before answering. Score 74.0%, vs Mem0's reported 68.5%. Letta's view: "memory is more about how agents manage context than the exact retrieval mechanism used" [VEN][LEX and DENSE, not separated] — [Letta](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- Audit (2026): full context with GPT-4.1-mini and a chain-of-thought answer prompt scores 92.62%. That is above EverMemOS's claimed 92.32% and its claimed full-context baseline of 91.21%. The auditor credits the gap to the answer prompt, not to memory [VEN-adjacent] — [locomo-audit](https://github.com/dial481/locomo-audit)

**Raw vs extracted on LongMemEval_S (GPT-4o reader unless noted)**
- LongMemEval paper: GPT-4o reading the full history scores 0.606 (0.640 with Chain-of-Note); reading only the evidence, 0.870 (0.924) [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- Emergence (Jun 18, 2025; the year is inferred from context). The retriever and reranker models are not named [VEN] — [Emergence](https://www.emergence.ai/blog/sota-on-longmemeval-with-rag):

  | Setup | Accuracy |
  |---|---|
  | Naive RAG over turns | 52.0% |
  | Full context, Zep's run | 60.2% |
  | Full context, Emergence's run | 63.8% |
  | Zep | 71.2% |
  | Full context, o3 reader | 76.0% |
  | "Simple Faster": as Simple Fast but 20 turns | 76.8% |
  | "Simple Fast": 42 turns, events and facts extracted at read time, then answer | 79.0% |
  | Accumulator: Chain-of-Note style, one session at a time (111.8 s per question) | 81.8% |
  | Evidence only, GPT-4o | 82.4% |
  | "Simple": match turns, return whole sessions ranked by NDCG of turns reranked by a cross-encoder, short chain of thought | 82.4% |
  | EmergenceMem Internal | 86.0% |
  | Evidence only, o3 reader | 92.0% |

- Emergence's conclusions: "RAG-like methods have largely solved the best LTM benchmark currently out there"; "advanced memory architecture appears to be overkill for LongMemEval"; "not just any RAG will crack this benchmark" [VEN] — [Emergence](https://www.emergence.ai/blog/sota-on-longmemeval-with-rag)
- Other vendor claims, which use different readers and judges and can't be compared directly (search summary) [VEN]:
  - Mastra Observational Memory: 94.87% with a gpt-5-mini reader, 93.27% with gemini-3-pro — [Mastra](https://mastra.ai/research/observational-memory). Mastra's earlier RAG: about 80% with gpt-4o — [Mastra RAG](https://mastra.ai/research/use-rag-for-agent-memory)
  - Supermemory: about 85% in production (85.2% with Gemini-3, 84.6% with GPT-5). An experimental "ASMR" scores about 99%, which Supermemory calls "not our main production Supermemory engine (yet)" — [Supermemory](https://supermemory.ai/blog/we-broke-the-frontier-in-agent-memory-introducing-99-sota-memory-system/)
  - Hindsight: 91.4% with Gemini-3, 89.0% with GPT-OSS 120B — [secondary article](https://emelia.io/hub/hindsight-ai-agent-memory)
  - ContextStream: 96.8% on its own run. Its competitors' numbers are copied from the vendors, not re-run — [ContextStream](https://contextstream.io/benchmarks)

**Independent evidence on raw vs extracted**
- MemoryAgentBench: BM25 over raw 512-token chunks scores 41.5 overall, vs Mem0 21.1, Zep 24.0, Cognee 20.6 and MemGPT 28.3. On LME(S*), BM25 scores 45.3 vs Mem0 36.0 and Zep 38.3 [IND][LEX] — [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- HaluMem: the Mem0 variants recall 2–43% of memory points; the best system recalls 74–82% (MemOS) [IND] — [HaluMem](https://arxiv.org/html/2511.03506)
- LongMemEval: facts help when added to keys (+9.4% recall, +5.4% QA) and hurt when they replace the raw text, except for multi-session questions [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- LoCoMo (2024): with a GPT-3.5 reader, observations beat raw turns at every k (41.4 vs 31.7 at top-5) [IND][DENSE] — [LoCoMo](https://arxiv.org/html/2402.17753)

**BM25 vs dense**
- LongMemEval Table 9 (Recall@5, sessions / rounds): BM25 0.634 / 0.472, Contriever 0.723 / 0.589, Stella V5 0.720 / 0.660. With fact keys, BM25 reaches 0.683 / 0.554 [IND][LEX] — [LongMemEval](https://arxiv.org/html/2410.10813)
- MemoryAgentBench: BM25 scores 41.5 overall vs Qwen3-Embedding-4B 38.2, text-embedding-3-large 38.0 and Contriever 29.8. Among BM25 and the embedding retrievers, BM25 is best on SH-QA (66.0), MH-QA (56.0) and EventQA (74.6), and below OpenAI embeddings on LME(S*) (45.3 vs 48.3 and 50.3). The paper only calls BM25 "entirely non-neural" and doesn't discuss the comparison [IND][LEX] — [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- None of the other sources isolates BM25. LoCoMo used only DRAGON (dense) — [LoCoMo](https://arxiv.org/html/2402.17753). Mem0's RAG baselines used only OpenAI embeddings — [Mem0 paper](https://arxiv.org/html/2504.19413). Letta's agent mixed grep with embedding search without separating their effects — [Letta](https://www.letta.com/blog/benchmarking-ai-agent-memory). LongMemCode includes a grep floor but publishes no results — [LongMemCode](https://github.com/CataDef/LongMemCode)

### Inferences
- Across sources, using facts as an index over raw text, with the raw text as the evidence, is supported. Using facts instead of raw text is not.
- Whether full context beats memory depends on how long the history is. On LoCoMo (16–26k tokens), full context beats every memory product. On LongMemEval_S (115k tokens), full-context GPT-4o (60–64%) loses to retrieval (71–86%). On MemoryAgentBench's LME(S*), long-context GPT-4o scores 32.0 vs BM25's 45.3. Coding-project histories that outgrow the context window fall on the retrieval side.
- The reader model moves scores as much as the memory design does. With perfect evidence, o3 beats GPT-4o by 9.6 points (92.0 vs 82.4) in the same harness. GPT-4o with evidence only scores 82.4 (Emergence), 87.0 and 92.4 (LongMemEval, without and with Chain-of-Note), depending on the prompt. Full context on LoCoMo ranges from 72.9 to 92.6 depending on model and prompt. Every vendor claim above about 92% on LongMemEval uses a newer reader.
- Mem0's own numbers show its trade-off. Computed from its Table 2: 6.0 J points below full context, for about 93% fewer tokens (1,764 vs 26,031) and about 92% lower p95 latency (1.44 s vs 17.1 s). The case for extraction is cost and latency, not accuracy.
- The best simple LongMemEval design (match on turns, return whole sessions, rerank, reason briefly) is the vendor version of LongMemEval's rounds-vs-sessions trade-off. Everything except the neural reranker fits a stdlib BM25 system.
- Letta claims that agentic, repeated searching matters more than the retriever. That claim is a vendor's, and it is confounded with embedding search.

### Gaps
- No source runs BM25 against dense retrieval on LoCoMo, or swaps BM25 into a vendor memory system.
- I found no independent re-run of the vendor LongMemEval claims.
- A later Zep figure of 90.2% (gpt-5.4 as reader and judge) appeared only in a search summary; I did not check its source page.
- Emergence doesn't name its embedding or reranker models, so its results can't be classed as lexical or dense.

## 5. Criticisms of reported numbers: vendor disputes, LLM judges, contamination, small categories

### Takeaway
The 2025 dispute between Mem0, Zep and Letta shows that LoCoMo rankings depend on who configured each rival system, on an unnamed or lenient LLM judge, on dropping the adversarial category, and on a 10-conversation test set whose answer key is 6.4% wrong, and some vendor claims collapse when others reproduce them (EverMemOS: 92.32% claimed, 38.38% re-run). LongMemEval's judge is better validated (over 97% agreement with experts), but the benchmark is close to saturated, vendor runs use different readers and judges, and some categories have only 30–56 questions, so gaps of a few points are within noise.

### Cited Findings
**Vendor disputes**
- Mem0 (Apr 28, 2025) ranked itself first on LoCoMo (Mem0g 68.44, Mem0 66.88, Zep 65.99, OpenAI 52.90), with full context higher still at 72.90 [VEN] — [Mem0 paper](https://arxiv.org/html/2504.19413)
- Zep (May 6, 2025) said Mem0 misconfigured Zep in three ways. Both speakers were given the user role in a single-user graph. Timestamps were put in the message text instead of Zep's created_at field. Searches were run one after another, which inflated latency (Zep's own p95 is 0.632 s vs the 0.778 s reported). Zep's corrected score is 75.14 ± 0.17, about 10% above Mem0g in relative terms, and Zep urged Mem0 to use LongMemEval [VEN] — [Zep](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)
- Letta (Aug 12, 2025) called Mem0's results "controversial". It said it could not load LoCoMo into MemGPT/Letta without major refactoring, and that Mem0 did not answer requests for clarification. It argued that "current memory benchmarks may not be very meaningful" and that comparing frameworks is "like comparing apples to oranges" [VEN] — [Letta](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- Audit (2026) [VEN-adjacent; the auditors are reportedly tied to a competing memory project (search summary)] — [locomo-audit](https://github.com/dial481/locomo-audit):
  - EverMemOS claims 92.32%, but third parties report 38.38% (EverMemOS issue #73);
  - EverMemOS's README says 2,298 tokens per question, but its paper's Table 8 shows 6,669 (GPT-4.1-mini) and 6,045 (GPT-4o-mini);
  - "multiple Mem0 reproducibility issues" are open;
  - some EverMemOS category scores are higher than the wrong golden answers make possible.

**How reliable the LLM judges are**
- LongMemEval's GPT-4o judge agrees with human experts over 97% of the time, checked on 30 sampled questions per type [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- LoCoMo's "J" score (introduced by Mem0's evaluation): the judge model is not named ("a separate, more capable LLM"), and the ± figures are SDs over 10 runs [VEN] — [Mem0 paper](https://arxiv.org/html/2504.19413)
- Using the same judge setup as the original evaluation, the audit submitted deliberately wrong answers. The judge accepted 62.81% of the vague but on-topic ones and 10.61% of the specific but wrong ones ("6x leniency") [VEN-adjacent] — [locomo-audit](https://github.com/dial481/locomo-audit). The write-up names the judge as gpt-4o-mini (search summary) — [Penfield Labs](https://dev.to/penfieldlabs/we-audited-locomo-64-of-the-answer-key-is-wrong-and-the-judge-accepts-up-to-63-of-intentionally-33lg)
- LoCoMo's original F1 metric is described both as exact-match F1 and as partial-match F1 [IND] — [LoCoMo](https://arxiv.org/html/2402.17753)

**Contamination and test-set reuse**
- LongMemEval doesn't discuss contamination, and half its filler sessions come from the public ShareGPT and UltraChat logs [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- LoCoMo was released with its answers under CC BY-NC 4.0 [IND] — [LoCoMo](https://arxiv.org/html/2402.17753)
- Supermemory's ~99% "ASMR" result comes from an experimental system that Supermemory says is not its production engine (search summary) [VEN] — [Supermemory](https://supermemory.ai/blog/we-broke-the-frontier-in-agent-memory-introducing-99-sota-memory-system/)
- Emergence says the benchmark "still isn't capturing important aspects of memory" [VEN] — [Emergence](https://www.emergence.ai/blog/sota-on-longmemeval-with-rag)

**Small or noisy categories, and metric confusion**
- In the LoCoMo public set, open-domain has 96 questions vs 841 in the largest category (8.8x), and the 446 adversarial questions usually go unscored [VEN-adjacent] — [locomo-audit](https://github.com/dial481/locomo-audit); [Zep](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/)
- LongMemEval's abstention category has 30 questions [IND] — [LongMemEval](https://arxiv.org/html/2410.10813)
- HaluMem warns that its under-2% update-hallucination rates rest on few samples [IND] — [HaluMem](https://arxiv.org/html/2511.03506)
- The best multi-hop forgetting score in MemoryAgentBench moved from at most 7% (earlier version, search summary) to at most 28% in v4, after GPT-5-mini was added — [Cognee guide](https://www.cognee.ai/agent-memory-evaluation-datasets-benchmarks); [MemoryAgentBench](https://arxiv.org/html/2507.05257)
- BEAM: Mem0 says its pass rate (70.1%) and its average score (0.641) are often confused (search summary) [VEN] — [Mem0](https://mem0.ai/library/agent-memory/how-to-read-memory-benchmarks)

### Inferences
- Sampling noise (95% binomial half-widths, my calculation):

  | Set | Questions | Typical score | ± points |
  |---|---|---|---|
  | LongMemEval overall | 500 | ~80% | 3.5 |
  | LoCoMo public, scored | 1,540 | ~70% | 2.3 |
  | LoCoMo open-domain | 96 | ~70% | 9.2 |
  | A 30-question category | 30 | ~50% | 18 |
  | A 200-question BEAM bucket | 200 | ~50% | 6.9 |

  Mem0's SDs of ±0.15–0.20 over 10 judge runs leave out question sampling. So the 1.6-point gap between Mem0 and Mem0g and the 0.9-point gap between Mem0 and Zep mean nothing. Paired comparisons on the same questions give narrower intervals.
- LongMemEval's per-type question counts can be recovered from Emergence's per-type percentages, since each is a multiple of 1/n: knowledge-update 78, multi-session 133, single-session-assistant 56, single-session-preference 30, single-session-user 70, temporal-reasoning 133, totalling 500. Preference scores swing from 13% to 70% across systems, and one question there is worth 3.3 points.
- Who configures a rival system matters more than most claimed margins: Zep scored 65.99 when Mem0 ran it and 75.14 when Zep did. Full-context LoCoMo runs differ by about 20 points (72.9 vs 92.6) with a different answer prompt and model.
- With 6.4% of golden answers wrong, a LoCoMo score above about 93.6% needs credit for wrong answers or a lenient judge. Because the judge also rewards vague answers, LoCoMo J tends to favour systems that answer vaguely over systems that abstain.
- Together these critiques suggest an evaluation recipe:
  - held-out questions;
  - the same reader model in every arm;
  - per-fact or strict judging, checked against human grades;
  - abstention scored separately;
  - several runs and paired tests;
  - losses reported alongside wins.

### Gaps
- I found no independent replication of the audit. The auditors reportedly build a competing memory system, so their numbers should be checked against the repository.
- I found no study measuring whether LoCoMo or LongMemEval content appears in model training data.
- I did not search for Mem0's reply to Zep's critique, if there was one.
- A dev.to post on "critical flaws in long-term memory benchmarks" (valesys) appeared in search results; I did not read it.

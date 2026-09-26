# Vera Engine — magicpin AI Challenge Submission

## 1. Approach & Architecture

We built Vera Engine around an **Opportunity & Decision Engine** rather than treating LLMs as raw marketing text generators.

### Key Architectural Layers:
1. **Context Store**: In-memory, versioned store (`ContextStore`) for dynamic context pushes (`CategoryContext`, `MerchantContext`, `TriggerContext`, `CustomerContext`).
2. **Opportunity Engine (`app/engine/opportunity.py`)**: Scores triggers on Value $\times$ Urgency using concrete context facts. Integrates linear time decay (`expires_at`) and suppresses non-actionable or un-consented outreach.
3. **Trigger Collision Arbitration & Fatigue**: Limits outreach to the single highest-scoring opportunity per merchant per tick and caps pressure at 3 sends per 24h window (except compliance alerts).
4. **Next Best Action Policy (`app/engine/next_best_action.py`)**: Decouples business workflow and CTA shape (`binary_yes_no`, `open_ended`, `binary_confirm_cancel`) from language generation.
5. **Evidence-First Composer (`app/composer/`)**: Bundles strict `FACT` and `DERIVED` tuples to eliminate hallucinations and enforce source citations (`"JIDA Oct 2026 p.14"`). Powered by Groq (`llama-3.3-70b-versatile`) with a deterministic template fallback.
6. **Adaptive Conversation State Machine**: Handles auto-reply detection with progressive backoff (4h $\rightarrow$ 24h $\rightarrow$ end), executes next steps on explicit merchant commitments, and gracefully exits on opt-outs (`STOP`/hostile).

---

## 2. Tradeoffs Made

- **Sequential Processing vs. Graph Frameworks**: Chosen explicit sequential Python decision pipelines over heavy agentic graph frameworks for low latency (< 100ms internal overhead) and determinism.
- **In-Memory Storage**: Opted for thread-safe in-memory stores (`ContextStore` & `EngagementStore`) over external relational databases, satisfying the challenge's state persistence rules while avoiding network roundtrips.
- **Deterministic Action Selection**: Decided business actions pre-LLM, ensuring workflow consistency and reliable WhatsApp template parameter formatting.

---

## 3. What Additional Context Would Have Helped Most

- **Granular Historical CTR by Time/Slot**: Detailed local CTR patterns for specific day parts would allow even finer-grained offer timing.
- **Explicit Merchant Schedule Constraints**: Real-time calendar availability beyond seed slot lists to optimize booking proposals.

#  Vera --- AI Engagement & Decision Engine

> A context-aware AI engagement engine built for the Magicpin Vera AI
> Challenge.

```{=html}
```
`<a href="https://vera-magicpin-ggiy.onrender.com">`{=html} Live
API`</a>`{=html} 
`<a href="https://vera-magicpin-ggiy.onrender.com/docs">`{=html} API
Docs`</a>`{=html} 
`<a href="https://github.com/Raunakkheshwani/Vera-MagicPin">`{=html}
GitHub`</a>`{=html}
```{=html}
```

------------------------------------------------------------------------

##  Overview

**Vera** is an AI-powered engagement and decision engine designed for
the Magicpin Vera AI Challenge.

Instead of treating every incoming trigger as an instruction to send a
message, Vera evaluates the complete business context and decides:

> **Should we act now, why now, what should we do, and how should that
> action be communicated?**

The system supports both:

-   **Vera  Merchant** communication
-   **Merchant-on-behalf-of  Customer** communication

The central design principle is:

> **A trigger is a signal, not an instruction to message.**

This separates **decision-making** from **language generation**,
allowing the system to reason about relevance, timing, fatigue,
evidence, conversation state, and the next best action before composing
the final message.

------------------------------------------------------------------------

##  Key Features

  -----------------------------------------------------------------------
  Feature                             Purpose
  ----------------------------------- -----------------------------------
   Opportunity Engine               Converts raw triggers into
                                      actionable business opportunities

   Context-Aware Decisions          Combines category, merchant,
                                      customer, and trigger context

   Why-Now Reasoning                Determines why an opportunity
                                      matters at the current moment

   Attention & Fatigue              Avoids unnecessary and repetitive
                                      outreach

   Trigger Arbitration              Resolves collisions between
                                      competing opportunities

   Opportunity Decay                Reduces priority as opportunities
                                      become stale

   Conversation State               Adapts behavior to the current
                                      conversation

   Next Best Action                 Selects the action before
                                      generating its wording

   Evidence-First Composition       Grounds messages in supplied facts

   Category Intelligence            Uses category-specific vocabulary,
                                      tone, and constraints

   Replay Handling                  Handles commitments, refusals,
                                      repeated replies, and off-topic
                                      messages

   Guardrails                       Reduces hallucination, malformed
                                      actions, unsupported claims, and
                                      unwanted outreach

   FastAPI                          Provides the official challenge API
                                      contract
  -----------------------------------------------------------------------

------------------------------------------------------------------------

#  Architecture

``` mermaid
flowchart TD
    A[Category Context] --> O[Opportunity Engine]
    B[Merchant Context] --> O
    C[Customer Context] --> O
    D[Trigger Context] --> O

    O --> E[Why-Now / Evidence]
    E --> F[Attention & Fatigue]
    F --> G[Trigger Arbitration]
    G --> H[Opportunity Decay]
    H --> I[Conversation State]
    I --> J[Next Best Action]
    J --> K[Evidence-First Composer]
    K --> L[Validated Action]

    L --> M[FastAPI]
    M --> N[/v1/context]
    M --> T[/v1/tick]
    M --> R[/v1/reply]
    M --> HZ[/v1/healthz]
    M --> MD[/v1/metadata]
```

### Decision Pipeline

``` text
Raw Context
    
Normalize Signals
    
Generate Opportunities
    
Evaluate Why-Now
    
Check Attention / Fatigue
    
Resolve Trigger Collisions
    
Apply Opportunity Decay
    
Understand Conversation State
    
Select Next Best Action
    
Gather Evidence
    
Compose Message
    
Validate Guardrails
    
Return Official Action
```

The important architectural distinction is:

``` text
Traditional bot:
Trigger  LLM  Message

Vera:
Trigger
   Context
   Opportunity
   Why Now
   Attention
   Arbitration
   Conversation State
   Next Best Action
   Evidence
   Composer
   Message
```

------------------------------------------------------------------------

#  Context Model

Vera operates on four primary context objects.

### CategoryContext

Category-level intelligence such as:

-   offer catalog
-   communication voice
-   peer statistics
-   research/digest information
-   seasonal beats
-   trend signals
-   allowed vocabulary and taboos

Supported categories:

-    Dentists
-    Salons
-    Restaurants
-    Gyms
-    Pharmacies

### MerchantContext

Represents the current state of a merchant:

``` text
merchant_id
category
identity
subscription
performance
offers
conversation_history
customer_aggregate
signals
```

### TriggerContext

Represents an event or signal:

``` text
trigger_id
scope
kind
source
merchant_id
customer_id
payload
urgency
suppression_key
expires_at
```

Examples include:

-   performance changes
-   customer lapse
-   appointment reminders
-   refill/compliance events
-   competitor activity
-   seasonal opportunities
-   milestones
-   research signals

### CustomerContext

Represents the relationship between a customer and merchant:

``` text
customer_id
merchant_id
identity
relationship
state
preferences
consent
```

Customer states include:

``` text
new
active
lapsed_soft
lapsed_hard
churned
```

------------------------------------------------------------------------

#  Opportunity Engine

A trigger does not automatically become a message.

For example:

``` text
Trigger:
IPL is trending
```

A naive system might immediately promote an IPL offer.

Vera instead evaluates:

``` text
Is the trend relevant to this merchant?
        
Does the merchant have a suitable offer?
        
Is the timing appropriate?
        
Has the merchant recently been contacted?
        
Is another opportunity stronger?
        
What action would actually help?
```

This transforms **event detection** into **business judgment**.

------------------------------------------------------------------------

#  Why-Now Reasoning

A useful action should have a concrete reason.

Conceptually:

``` json
{
  "decision": "SEND",
  "opportunity": {
    "type": "performance_dip",
    "urgency": 4,
    "why_now": [
      "7-day views are declining",
      "merchant has an active relevant offer"
    ]
  }
}
```

The final message can then be tied to actual context rather than generic
promotional copy.

------------------------------------------------------------------------

#  Attention, Fatigue & Suppression

Repeated outreach can reduce engagement.

Vera considers:

-   recent sends
-   conversation activity
-   repeated triggers
-   suppression keys
-   previous interaction state

The system can therefore distinguish between:

``` text
Important opportunity
```

and:

``` text
Important opportunity + bad timing
```

The second case may be delayed or suppressed.

------------------------------------------------------------------------

#  Trigger Arbitration

Several opportunities may arrive simultaneously:

``` text
Performance dip
+
Customer lapse
+
Festival opportunity
+
Competitor activity
```

Instead of sending four unrelated messages, Vera evaluates competing
opportunities and chooses an appropriate next action.

------------------------------------------------------------------------

#  Opportunity Decay

Opportunity value can decrease as:

-   time passes
-   a trigger expires
-   business context changes
-   the merchant responds
-   a stronger opportunity appears

This prevents stale events from dominating newer and more relevant
signals.

------------------------------------------------------------------------

#  Conversation Intelligence

Vera maintains conversational intent rather than treating every response
as an isolated request.

### Explicit commitment

If a merchant indicates a clear commitment, the system can move to the
next execution step rather than repeatedly qualifying the same intent.

### Hard refusal

A clear refusal or stop request leads to graceful termination and
suppression of unnecessary future outreach.

### Repeated automated replies

Repeated automatic replies can trigger progressively longer backoff and
eventual termination.

### Off-topic responses

The system redirects or declines without inventing unsupported
information.

------------------------------------------------------------------------

#  Evidence-First Composition

The composer is designed around:

``` text
Decision
   
Evidence
   
Action
   
CTA
   
Message
```

This helps keep generated communication grounded in supplied context.

For research and compliance-oriented messages, source/provenance
information can be preserved where available.

------------------------------------------------------------------------

#  Category Intelligence

##  Dentists

**Voice:** peer-clinical, respectful, collegial

**Vocabulary:** fluoride varnish, scaling, caries, RCT, OPG, IOPA

**Avoid:** guaranteed, 100% safe, miracle, best in city, cure

##  Salons

**Voice:** warm, practical, approachable expert

**Vocabulary:** balayage, keratin, smoothening, facial, threading

**Avoid:** guaranteed glow, permanent results, instant transformation

##  Restaurants

**Voice:** warm, busy, practical, fellow-operator

**Vocabulary:** footfall, covers, AOV, RPC, thali, biryani, tandoor

**Avoid:** best food in city, guaranteed packed house, viral guarantee

##  Gyms

**Voice:** energetic, disciplined, coach-to-member

**Vocabulary:** membership churn, PT, PR, 1RM, HIIT, BMR, yoga

**Avoid:** guaranteed weight loss, shred in 7 days, miracle
transformation

##  Pharmacies

**Voice:** trustworthy, precise, neighbourhood pharmacist

**Vocabulary:** OTC, molecule, MRP, expiry, batch, pharmacist counsel

**Avoid:** miracle cure, guaranteed result, 100% safe, unsupported
doctor recommendation

------------------------------------------------------------------------

#  API

## Production

**Base URL**

``` text
https://vera-magicpin-ggiy.onrender.com
```

**Swagger / OpenAPI UI**

``` text
https://vera-magicpin-ggiy.onrender.com/docs
```

### `GET /v1/healthz`

Health and liveness endpoint.

### `GET /v1/metadata`

Returns service metadata such as team, model, approach, and version.

### `POST /v1/context`

Ingests versioned category, merchant, trigger, and customer context.

### `POST /v1/tick`

Evaluates current opportunities and returns proactive engagement
actions.

A typical action can contain:

``` json
{
  "conversation_id": "...",
  "merchant_id": "...",
  "customer_id": "...",
  "send_as": "...",
  "trigger_id": "...",
  "template_name": "...",
  "template_params": {},
  "body": "...",
  "cta": "...",
  "suppression_key": "...",
  "rationale": "..."
}
```

### `POST /v1/reply`

Processes a merchant/customer reply.

Possible outcomes:

``` text
send
wait
end
```

------------------------------------------------------------------------

#  Project Structure

``` text
Vera-MagicPin/

 magicpin-ai-challenge/
    judge_simulator.py
    ...

 vera-engine/
    app/
       __init__.py
       main.py
       api/
       composer/
       engine/
       models/
       state/
   
    tests/
       test_context_models.py
   
    requirements.txt
    pytest.ini
    .env.example
    .gitignore

 README.md
```

The official challenge material is kept separate from the custom Vera
engine implementation.

------------------------------------------------------------------------

#  Tech Stack

### Backend

-   Python
-   FastAPI
-   Uvicorn
-   Pydantic

### AI

-   Google Gemini
-   Context-grounded generation
-   Evidence-first composition

### Testing

-   Pytest
-   API validation
-   Challenge judge simulator
-   Replay-oriented testing

### Deployment

-   GitHub
-   Render

------------------------------------------------------------------------

#  Local Setup

### 1. Clone

``` bash
git clone https://github.com/Raunakkheshwani/Vera-MagicPin.git
cd Vera-MagicPin
```

### 2. Enter the engine

``` bash
cd Vera-MagicPin/vera-engine
```

### 3. Create a virtual environment

``` bash
python -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

``` bash
pip install -r requirements.txt
```

### 5. Configure environment

Create `.env`:

``` env
GEMINI_API_KEY=your_api_key_here
LLM_PROVIDER=gemini
LLM_MODEL=your_model_name
```

Never commit `.env`. Use `.env.example` as the public template.

### 6. Start locally

``` bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then visit:

``` text
http://localhost:8000/docs
http://localhost:8000/v1/healthz
```

------------------------------------------------------------------------

#  Testing

Run model tests:

``` bash
pytest tests/test_context_models.py -v
```

Run all tests:

``` bash
pytest -v
```

------------------------------------------------------------------------

#  Challenge Simulator

Local:

``` bash
python magicpin-ai-challenge/judge_simulator.py
```

Against the deployed API:

``` bash
export BOT_URL="https://vera-magicpin-ggiy.onrender.com"
python magicpin-ai-challenge/judge_simulator.py
```

The production evaluation path is:

``` text
Judge Simulator
      
Public HTTPS
      
Render
      
FastAPI
      
Vera Engine
      
Challenge Evaluation
```

------------------------------------------------------------------------

#  Render Deployment

The deployed service uses:

**Runtime**

``` text
Python 3
```

**Root Directory**

``` text
Vera-MagicPin/vera-engine
```

**Build Command**

``` bash
pip install -r requirements.txt
```

**Start Command**

``` bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Health Check**

``` text
/v1/healthz
```

The current production deployment is available at:

``` text
https://vera-magicpin-ggiy.onrender.com
```

> The free Render instance may spin down after inactivity, causing a
> cold-start delay. For time-sensitive evaluation, verify that the
> service is awake and healthy before starting the judge.

------------------------------------------------------------------------

#  Evaluation

The deployed version was tested using the challenge judge simulator.

  Check                       Result
  --------------------------- ---------
  Deployment                   PASS
  Health checks                PASS
  Context ingestion            PASS
  API interaction              PASS
  Judge simulation             PASS
  Observed evaluation score   **76%**

Because the evaluation contains LLM-based judging, individual runs can
vary. The development goal is therefore to improve average decision
quality and robustness across scenarios rather than optimize a single
run.

------------------------------------------------------------------------

#  Reliability & Guardrails

Vera is designed around several failure-prevention principles:

### No fabricated business facts

The system should not invent:

-   prices
-   performance statistics
-   offers
-   customer information
-   unsupported business metrics

### No unsupported medical claims

Dental and pharmacy communication follows category-specific constraints
and avoids unsupported guarantees or medical claims.

### One primary CTA

Messages focus on a clear next action rather than multiple competing
requests.

### Conversation-aware suppression

Repeated, rejected, hostile, or stale interactions can be suppressed or
ended.

### Operational resilience

The service exposes a dedicated health endpoint and is designed to
handle challenge context updates and replay-style conversations.

------------------------------------------------------------------------

#  Security

Secrets belong in environment variables, never in Git.

``` env
GEMINI_API_KEY=...
```

The repository should contain:

``` text
.env.example
```

and should exclude:

``` text
.env
```

If a credential is ever exposed:

1.  revoke or rotate it
2.  remove it from source/history
3.  update the deployment secret
4.  redeploy
5.  verify the service

------------------------------------------------------------------------

#  Design Philosophy

The project is built around one core question:

> **What is the best action for this business situation right now?**

Not:

> **What message can the LLM generate?**

That leads to a deliberate separation:

``` text
Signals
   
Reasoning
   
Decision
   
Evidence
   
Action
   
Language
```

This makes the LLM a **communication layer inside a larger decision
system**, rather than allowing the LLM to act as the entire decision
engine.

------------------------------------------------------------------------

#  Future Improvements

Potential extensions include:

-   persistent conversation memory
-   richer merchant digital twins
-   learned opportunity scoring
-   outcome-based feedback loops
-   adaptive attention budgets
-   A/B testing of action strategies
-   stronger provenance tracking
-   automated regression evaluation
-   model fallback and provider routing
-   richer observability and decision traces
-   category-specific policy modules

------------------------------------------------------------------------

#  Author

**Raunak Kheshwani**

Computer Science & Engineering\
Jaypee Institute of Information Technology, Noida

**Interests**

`AI`  `Generative AI`  `LLM Systems`  `RAG`  `AI Agents` 
`Machine Learning`  `Backend Engineering`

------------------------------------------------------------------------

#  Challenge

Built for the **Magicpin Vera AI Challenge**.

The implementation follows the provided challenge context contracts, API
expectations, evaluation workflow, and messaging constraints.

------------------------------------------------------------------------

```{=html}
```
``{=html}Vera doesn't just ask "What should I say?"``{=html}
`<br/>`{=html} ``{=html}It first asks "Should I act, why now, and
what action creates value?"``{=html}
```{=html}
```

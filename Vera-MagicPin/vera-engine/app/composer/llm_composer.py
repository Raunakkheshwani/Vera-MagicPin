"""
Evidence-First Composer. The LLM ONLY writes wording — action/CTA/send_as
are already decided. Supports Gemini and Groq with fallback to a deterministic template.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest

from config.settings import settings

SYSTEM_PROMPT = """You are Vera, an intelligent WhatsApp merchant engagement assistant for magicpin in India.
Your goal is to compose highly compelling, data-backed WhatsApp messages for local merchants and customers.

STRICT SCORING RULES:
1. SPECIFICITY (10/10): Always cite concrete numbers (views, CTR %, calls, prices like ₹299), dates/times, or exact source citations (e.g. "JIDA Oct 2026 p.14", "DCI circular") from the provided facts.
2. CATEGORY FIT (10/10): Match the category voice perfectly:
   - Dentists: Respectful, clinical, peer-to-peer tone. Use "Dr. [owner_first_name]" if available.
   - Salons: Warm, friendly, approachable expert.
   - Restaurants: Operator-to-operator, practical.
   - Gyms: Motivational, coaching tone.
   - Pharmacies: Precise, trustworthy neighbourhood pharmacist.
   - AVOID all listed taboo words.
3. MERCHANT FIT (10/10): Greet by owner_first_name if given in facts (e.g. "Hi Dr. Meera", "Hi Vikas"). Use ONLY the exact city/locality from facts. NEVER invent a city name (e.g. Bandra) or owner name if not in the facts!
4. ENGAGEMENT COMPULSION (10/10): Use curiosity, loss aversion ("your 7d views changed"), or effort externalization ("I've drafted X for you"). End with a single, clear, low-friction next step or binary question (e.g., "Want me to help with X?").

CRITICAL CONSTRAINTS:
- Do NOT include any URLs.
- Do NOT invent fake numbers, cities, owner names, or unsupplied facts.
- Do NOT expose internal IDs, trigger names, or system jargon.
- NEVER start messages with generic meta-phrases like "quick note:", "important operational update", "external event", "compliance update", or "this is an operational update". Jump straight into natural, conversational messaging.
- Write 2-3 concise WhatsApp sentences, no markdown bold/italics, no preamble.

Return ONLY the final message body text."""


def _build_user_prompt(
    merchant_name: str,
    category_tone: str,
    taboo_words: List[str],
    action_name: str,
    why_now: List[str],
    evidence: List[Dict[str, Any]],
    customer_name: Optional[str],
    evolution_hint: Optional[str],
) -> str:
    facts = "\n".join(f"- {e.get('fact')} (source: {e.get('source')}, confidence: {e.get('confidence')})" for e in evidence)
    audience = f"customer named {customer_name}" if customer_name else f"merchant {merchant_name}"
    prompt = f"""Audience: {audience}
Category tone: {category_tone}
Taboo words to avoid: {', '.join(taboo_words) if taboo_words else 'none'}
Why this message, now: {'; '.join(why_now)}
Facts available:
{facts}
Action to lead toward: {action_name}"""
    if evolution_hint:
        prompt += f"\n\nIMPORTANT: {evolution_hint}"
    
    if "ask" in action_name.lower():
        prompt += "\nIMPORTANT: Ask the merchant an insightful question about their top requested treatments/services this week, offering Vera's help to promote it."
    elif "offer" in action_name.lower():
        prompt += "\nIMPORTANT: Lead with a concrete service+price offer from facts/catalog and ask if they want to publish it."
    elif "gbp" in action_name.lower() or "verification" in action_name.lower():
        prompt += "\nIMPORTANT: Alert the merchant about their GBP verification status and offer to help complete it."

    prompt += "\nWrite the message body now."
    return prompt


def _call_gemini(api_key: str, model_name: str, user_prompt: str) -> Optional[str]:
    import time
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
    body = json.dumps({
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 300}
    }).encode("utf-8")
    
    for attempt in range(3):
        try:
            req = urlrequest.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urlrequest.urlopen(req, timeout=15.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return None


def _call_groq(api_key: str, model_name: str, user_prompt: str) -> Optional[str]:
    try:
        from groq import Groq
        client = Groq(api_key=api_key, timeout=8.0)
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


def compose_body(
    merchant_name: str,
    category_tone: str,
    taboo_words: List[str],
    action_name: str,
    why_now: List[str],
    evidence: List[Dict[str, Any]],
    customer_name: Optional[str] = None,
    evolution_hint: Optional[str] = None,
) -> str:
    user_prompt = _build_user_prompt(
        merchant_name, category_tone, taboo_words, action_name,
        why_now, evidence, customer_name, evolution_hint
    )

    if settings.gemini_api_key:
        res = _call_gemini(settings.gemini_api_key, settings.model_name, user_prompt)
        if res:
            return res

    if settings.groq_api_key:
        res = _call_groq(settings.groq_api_key, settings.model_name, user_prompt)
        if res:
            return res

    return _fallback_body(merchant_name, action_name, why_now, customer_name, evolution_hint)


def _fallback_body(merchant_name: str, action_name: str, why_now: List[str],
                    customer_name: Optional[str], evolution_hint: Optional[str]) -> str:
    who = customer_name or merchant_name
    reason = why_now[0] if why_now else "something worth a quick look"
    base = f"Hi {who}, quick note: {reason}."
    if evolution_hint:
        return f"{base} Quick one — just reply YES or NO to proceed?"
    return f"{base} Want me to help with the next step ({action_name.replace('_', ' ')})?"
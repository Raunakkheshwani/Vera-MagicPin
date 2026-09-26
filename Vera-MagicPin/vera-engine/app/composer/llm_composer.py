"""
Evidence-First Composer. The LLM ONLY writes wording — action/CTA/send_as
are already decided. Supports Gemini and Groq with fallback to a deterministic template.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest

from config.settings import settings

SYSTEM_PROMPT = """You are Vera's message composer for a merchant engagement WhatsApp bot.
Rules:
- Use ONLY the facts given to you. Never invent a number, offer, source, date, or outcome.
- Match the given category voice/tone. Avoid any taboo words listed.
- Write ONE short WhatsApp-style message (2-4 sentences max), no preamble, no markdown, no quotes.
- End with a natural lead-in to the given action — do not literally write the CTA type.
- Do not include any URL.
- Do not mention internal IDs, trigger names, or system jargon.
Return ONLY the message body text, nothing else."""


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
    prompt += "\nWrite the message body now."
    return prompt


def _call_gemini(api_key: str, model_name: str, user_prompt: str) -> Optional[str]:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
        body = json.dumps({
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300}
        }).encode("utf-8")
        req = urlrequest.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urlrequest.urlopen(req, timeout=8.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
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
            temperature=0.4,
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
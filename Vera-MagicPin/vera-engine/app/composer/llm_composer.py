"""
Evidence-First Composer. The LLM ONLY writes wording — action/CTA/send_as
are already decided. Falls back to a deterministic template if Groq is
unset/slow/fails. `evolution_hint` (from message_evolution.py) adjusts
wording strategy on repeat attempts without changing the decided action.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.settings import settings

_client = None


def _get_client():
    global _client
    if _client is None and settings.groq_api_key:
        from groq import Groq
        _client = Groq(api_key=settings.groq_api_key, timeout=8.0)
    return _client


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
    client = _get_client()
    if client is not None:
        try:
            resp = client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(
                        merchant_name, category_tone, taboo_words, action_name,
                        why_now, evidence, customer_name, evolution_hint
                    )},
                ],
                temperature=0.4,
                max_tokens=200,
            )
            body = resp.choices[0].message.content.strip()
            if body:
                return body
        except Exception:
            pass

    return _fallback_body(merchant_name, action_name, why_now, customer_name, evolution_hint)


def _fallback_body(merchant_name: str, action_name: str, why_now: List[str],
                    customer_name: Optional[str], evolution_hint: Optional[str]) -> str:
    who = customer_name or merchant_name
    reason = why_now[0] if why_now else "something worth a quick look"
    base = f"Hi {who}, quick note: {reason}."
    if evolution_hint:
        return f"{base} Quick one — just reply YES or NO to proceed?"
    return f"{base} Want me to help with the next step ({action_name.replace('_', ' ')})?"
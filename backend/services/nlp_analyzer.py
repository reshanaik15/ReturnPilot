"""
NLP Analysis Service for ReturnPilot.

Uses Gemini (via Google AI Studio) as a classifier to:
1. Classify return reasons into structured categories
2. Extract customer sentiment (frustrated / neutral / polite)
3. Suggest appropriate response tone for the agent

This runs as a lightweight LLM call separate from the main agent loop,
feeding structured metadata into the return record and analytics dashboard.
"""

import json
import logging
from typing import Optional
import httpx

from config import settings

logger = logging.getLogger(__name__)

# Return reason taxonomy
REASON_CATEGORIES = [
    "defective",           # Product doesn't work / broken on arrival
    "wrong_item",          # Received wrong product
    "size_mismatch",       # Wrong size / doesn't fit
    "not_as_described",    # Product differs from listing/images
    "change_of_mind",      # No longer wants / found better deal
    "damaged_in_transit",  # Damaged during shipping
    "other",               # Doesn't fit other categories
]

SENTIMENT_CATEGORIES = ["frustrated", "neutral", "polite"]

CLASSIFIER_SYSTEM_PROMPT = """You are a return reason classifier for an e-commerce returns system.
Your job is to analyze a customer's return request and extract structured information.

You must respond with ONLY a valid JSON object — no explanation, no markdown, no code blocks.

Return exactly this structure:
{
    "reason_classification": "<one of: defective|wrong_item|size_mismatch|not_as_described|change_of_mind|damaged_in_transit|other>",
    "confidence": <float between 0.0 and 1.0>,
    "sentiment": "<one of: frustrated|neutral|polite>",
    "keywords": ["<keyword1>", "<keyword2>"],
    "suggested_response_tone": "<one of: empathetic|informative|apologetic>",
    "brief_summary": "<one sentence summary of the issue>"
}"""


async def analyze_return_reason(
    message: str,
    reason: Optional[str] = None,
) -> dict:
    """
    Classify a customer's return message using Claude.

    Args:
        message: The customer's original chat message
        reason: The extracted return reason (if already parsed), optional

    Returns:
        NLP analysis dict with classification, sentiment, keywords, tone
    """
    text_to_analyze = reason if reason else message

    user_content = f"""Analyze this customer return request:

"{text_to_analyze}"

Classify the return reason, detect sentiment, and extract keywords."""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.google_api_key}",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.google_model,
                    "max_tokens": 300,
                    "reasoning_effort": "low",
                    "messages": [
                        {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()

        raw_text = data["choices"][0]["message"]["content"].strip()
        # Strip markdown code fences some models wrap JSON in despite instructions
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        # Parse JSON response
        analysis = json.loads(raw_text)

        # Validate fields
        if analysis.get("reason_classification") not in REASON_CATEGORIES:
            analysis["reason_classification"] = "other"
        if analysis.get("sentiment") not in SENTIMENT_CATEGORIES:
            analysis["sentiment"] = "neutral"
        if not isinstance(analysis.get("confidence"), (int, float)):
            analysis["confidence"] = 0.7

        logger.info(
            f"NLP analysis: classification={analysis['reason_classification']}, "
            f"sentiment={analysis['sentiment']}, confidence={analysis['confidence']}"
        )
        return analysis

    except json.JSONDecodeError as e:
        logger.warning(f"NLP classifier returned invalid JSON: {e}")
        return _fallback_analysis(text_to_analyze)
    except httpx.TimeoutException:
        logger.warning("NLP classifier timed out, using fallback")
        return _fallback_analysis(text_to_analyze)
    except Exception as e:
        logger.error(f"NLP analysis error: {e}", exc_info=True)
        return _fallback_analysis(text_to_analyze)


def _fallback_analysis(text: str) -> dict:
    """
    Rule-based fallback when Claude classifier is unavailable.
    Uses simple keyword matching.
    """
    text_lower = text.lower()

    # Simple keyword-based classification
    if any(w in text_lower for w in ["broken", "defect", "doesn't work", "not working", "faulty"]):
        classification = "defective"
    elif any(w in text_lower for w in ["wrong item", "wrong product", "different item"]):
        classification = "wrong_item"
    elif any(w in text_lower for w in ["size", "fit", "too big", "too small", "tight", "loose"]):
        classification = "size_mismatch"
    elif any(w in text_lower for w in ["not as described", "different from", "misleading", "false"]):
        classification = "not_as_described"
    elif any(w in text_lower for w in ["damaged", "crushed", "broken in", "arrived damaged"]):
        classification = "damaged_in_transit"
    elif any(w in text_lower for w in ["changed mind", "don't want", "no longer", "found better"]):
        classification = "change_of_mind"
    else:
        classification = "other"

    # Simple sentiment
    if any(w in text_lower for w in ["terrible", "awful", "angry", "frustrated", "unacceptable", "worst"]):
        sentiment = "frustrated"
    elif any(w in text_lower for w in ["please", "thank", "appreciate", "kindly"]):
        sentiment = "polite"
    else:
        sentiment = "neutral"

    return {
        "reason_classification": classification,
        "confidence": 0.6,
        "sentiment": sentiment,
        "keywords": [w for w in text_lower.split() if len(w) > 4][:5],
        "suggested_response_tone": "empathetic" if sentiment == "frustrated" else "informative",
        "brief_summary": text[:100],
        "fallback": True,
    }

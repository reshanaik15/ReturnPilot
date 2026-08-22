"""
Photo Damage Verification Service for ReturnPilot.

Uses Gemini (via Google AI Studio) to check whether a customer's
uploaded return-evidence photo is consistent with their claimed issue.
"""

import json
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

VERDICT_SYSTEM_PROMPT = """You are a returns quality analyst reviewing photo evidence for a product return.
You will be shown a photo and the customer's claimed issue with the product.

You must respond with ONLY a valid JSON object — no explanation, no markdown, no code blocks.

Return exactly this structure:
{
    "consistent": <true if the photo plausibly shows the claimed issue, false otherwise>,
    "confidence": "<one of: high|medium|low>",
    "notes": "<one or two sentence explanation of your assessment>"
}"""


async def analyze_damage_photo(
    image_base64: str,
    claimed_issue: str,
    content_type: str = "image/jpeg",
) -> dict:
    """
    Analyze a return-evidence photo against the customer's claimed issue.

    Returns:
        {"consistent": bool, "confidence": "high"|"medium"|"low", "notes": str}

    Falls back to a conservative low-confidence "inconsistent" result if the
    vision call fails or returns unparseable output, so the return gets
    routed to human review rather than silently trusting an unverified photo.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                        {"role": "system", "content": VERDICT_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"Claimed issue: {claimed_issue}"},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{content_type};base64,{image_base64}"},
                                },
                            ],
                        },
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()

        raw_text = data["choices"][0]["message"]["content"].strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        verdict = json.loads(raw_text)
        if verdict.get("confidence") not in ("high", "medium", "low"):
            verdict["confidence"] = "low"
        if not isinstance(verdict.get("consistent"), bool):
            verdict["consistent"] = False

        logger.info(
            f"Photo verdict: consistent={verdict['consistent']}, confidence={verdict['confidence']}"
        )
        return verdict

    except Exception as e:
        logger.error(f"Photo verification failed: {e}", exc_info=True)
        return {
            "consistent": False,
            "confidence": "low",
            "notes": "Automated photo analysis failed; flagged for manual review.",
        }

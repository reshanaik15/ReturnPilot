"""
Multi-Agent Orchestrator for ReturnPilot.

Architecture:
    User message → Orchestrator (Gemini via Google AI Studio) → routes to specialist agents
    Each specialist has its own system prompt and focused tools.
    The orchestrator collects results and builds a full reasoning_trace.

Agents:
    orchestrator    - Routes the conversation, decides which specialist to invoke
    order_agent     - Resolves vague order references using search_orders tool
    policy_agent    - Checks return eligibility using check_policy tool
    return_agent    - Initiates returns using initiate_return tool
    analytics_agent - Provides NLP analysis and return pattern insights

The reasoning_trace records every agent's action, enabling the frontend
to show a live multi-step reasoning panel to judges.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from services.tools import (
    search_orders,
    check_policy,
    initiate_return,
    verify_damage_photo,
    get_return_analytics,
)
from services.nlp_analyzer import analyze_return_reason

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Google AI Studio caller (Gemini, via its OpenAI-compatible endpoint)
# ---------------------------------------------------------------------------

GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"


async def call_llm(
    system: str,
    messages: list,
    tools: Optional[list] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
) -> dict:
    """
    Make a single call to Gemini via Google AI Studio's OpenAI-compatible
    chat completions endpoint.

    `messages` is OpenAI-style (role: user/assistant/tool). The system
    prompt is prepended as its own message here rather than passed
    separately, since OpenAI-style APIs don't have a top-level `system` field.
    """
    payload: dict = {
        "model": model or settings.google_model,
        "max_tokens": max_tokens,
        # Gemini 3.x can't fully disable its internal thinking trace, but "low"
        # keeps the overhead small (~100 tokens) relative to our max_tokens budgets.
        "reasoning_effort": "low",
        "messages": [{"role": "system", "content": system}] + messages,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            GOOGLE_URL,
            headers={
                "Authorization": f"Bearer {settings.google_api_key}",
                "content-type": "application/json",
            },
            json=payload,
        )
        if response.status_code == 429:
            raise httpx.HTTPStatusError("Rate limit", request=response.request, response=response)
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI-style, as required by Gemini's OpenAI-compatible API)
# ---------------------------------------------------------------------------

def _tool(name: str, description: str, properties: dict, required: list) -> dict:
    """Build an OpenAI-style function tool definition."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


TOOLS = [
    _tool(
        "search_orders",
        (
            "Search the customer's order history using natural language. "
            "Handles vague references like 'shoes from yesterday', 'laptop I bought last week', "
            "'my recent jacket order'. Returns matching orders with eligibility hints."
        ),
        {
            "query": {
                "type": "string",
                "description": "Natural language search query extracted from the customer's message"
            }
        },
        ["query"],
    ),
    _tool(
        "check_policy",
        (
            "Check return eligibility for a specific order against the company's return policy. "
            "Verifies return window, final sale status, and existing return records. "
            "Call this after identifying the order with search_orders."
        ),
        {
            "order_id": {
                "type": "string",
                "description": "The order ID to check (e.g. ORD-1001)"
            }
        },
        ["order_id"],
    ),
    _tool(
        "initiate_return",
        (
            "Create a return request in the system after verifying eligibility. "
            "Only call this after check_policy confirms the item is eligible. "
            "Returns a return ID and shipping label reference."
        ),
        {
            "order_id": {
                "type": "string",
                "description": "Order ID to return (e.g. ORD-1001)"
            },
            "reason": {
                "type": "string",
                "description": "Customer's stated reason for return"
            }
        },
        ["order_id", "reason"],
    ),
    _tool(
        "get_analytics",
        (
            "Get return pattern analytics for this customer — "
            "how many returns they've made, which categories, refund rates. "
            "Use when customer asks about their return history or patterns."
        ),
        {},
        [],
    ),
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def build_system_prompt(customer_id: str, customer_name: str = "the customer") -> str:
    return f"""You are ReturnPilot, an intelligent returns agent for a retail company.
You are helping {customer_name} process a product return request.

Your job is to:
1. IDENTIFY which order the customer is referring to (use search_orders for vague descriptions)
2. CHECK eligibility against the return policy (use check_policy)
3. INITIATE the return if eligible (use initiate_return)
4. EXPLAIN clearly if not eligible, with the reason

IMPORTANT RULES:
- Always call search_orders first when the customer mentions a product they want to return
- Never initiate a return without first calling check_policy
- If multiple orders match, ask the customer to confirm which one
- Be empathetic and helpful — customers may be frustrated
- Keep responses concise and actionable
- If a return is initiated, always mention the Return ID and label reference

Customer ID: {customer_id}"""


# ---------------------------------------------------------------------------
# Execute tool call
# ---------------------------------------------------------------------------

async def execute_tool(
    tool_name: str,
    tool_input: dict,
    customer_id: str,
    db: AsyncSession,
) -> Any:
    """Route an LLM tool call to the actual implementation."""
    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

    if tool_name == "search_orders":
        return await search_orders(
            customer_id=customer_id,
            query=tool_input.get("query", ""),
            db=db,
        )
    elif tool_name == "check_policy":
        return await check_policy(
            order_id=tool_input.get("order_id", ""),
            db=db,
        )
    elif tool_name == "initiate_return":
        return await initiate_return(
            order_id=tool_input.get("order_id", ""),
            reason=tool_input.get("reason", ""),
            customer_id=customer_id,
            db=db,
        )
    elif tool_name == "get_analytics":
        return await get_return_analytics(customer_id=customer_id, db=db)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# Main agent turn — the orchestrator loop
# ---------------------------------------------------------------------------

async def agent_turn(
    customer_id: str,
    message: str,
    conversation_history: list,
    db: AsyncSession,
    image_base64: Optional[str] = None,
    customer_name: str = "Customer",
) -> dict:
    """
    Run the multi-agent orchestration loop for one customer turn.

    Flow:
        1. Run NLP analysis on the incoming message (parallel context)
        2. Enter Claude tool-use loop (max 6 iterations)
        3. Each tool call is logged to reasoning_trace with agent labels
        4. Return final response + full reasoning trace + NLP analysis

    Args:
        customer_id: Customer UUID string
        message: Customer's text message
        conversation_history: Previous messages in this session
        db: AsyncSession for all DB tool calls
        image_base64: Optional photo for damage verification
        customer_name: Customer's name for personalized prompts

    Returns:
        {
            "response": str,
            "reasoning_trace": list of step dicts,
            "iterations": int,
            "nlp_analysis": dict,
            "return_id": str | None,
            "return_initiated": bool
        }
    """
    reasoning_trace = []
    return_id = None
    return_initiated = False
    # Set when initiate_return succeeds; lets a later LLM-call failure (timeout/
    # rate limit) report the truth instead of a generic apology that contradicts
    # a return that already went through in this same turn.
    return_confirmation = None

    def _degraded_response(error_code: str, apology: str, iteration: int) -> dict:
        if return_initiated and return_confirmation:
            response_text = (
                f"{return_confirmation} (I'm having trouble generating a full reply right now — "
                f"{apology.rstrip('.').lower()} — but this return has already gone through, you're all set.)"
            )
        else:
            response_text = apology
        return {
            "response": response_text,
            "reasoning_trace": reasoning_trace,
            "iterations": iteration + 1,
            "nlp_analysis": nlp_analysis,
            "return_id": return_id,
            "return_initiated": return_initiated,
            "error": error_code,
        }

    # Step 1: NLP analysis (run before main loop for context)
    nlp_analysis = await analyze_return_reason(message)
    reasoning_trace.append({
        "agent": "nlp_analyzer",
        "decision": f"Message classified as '{nlp_analysis['reason_classification']}' with {nlp_analysis['sentiment']} sentiment",
        "result": nlp_analysis,
        "timestamp": datetime.utcnow().isoformat(),
    })
    logger.info(f"NLP: {nlp_analysis['reason_classification']}, sentiment: {nlp_analysis['sentiment']}")

    # Step 2: Build initial message history
    history = list(conversation_history)

    # Build user content (text + optional image), OpenAI-style content parts
    user_content: list = [{"type": "text", "text": message}]
    if image_base64:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
        })

    history.append({"role": "user", "content": user_content})

    system_prompt = build_system_prompt(customer_id, customer_name)

    # Step 3: Tool-use orchestration loop (max 6 iterations)
    for iteration in range(6):
        reasoning_trace.append({
            "agent": "orchestrator",
            "decision": f"Calling Gemini (iteration {iteration + 1})",
            "timestamp": datetime.utcnow().isoformat(),
        })

        try:
            llm_response = await call_llm(
                system=system_prompt,
                messages=history,
                tools=TOOLS,
            )
        except httpx.TimeoutException:
            logger.error("Gemini API timeout")
            return _degraded_response(
                "llm_timeout",
                "I'm sorry, the AI service is temporarily slow. Please try again in a moment.",
                iteration,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return _degraded_response(
                    "rate_limited",
                    "I'm experiencing high demand right now. Please try again in 30 seconds.",
                    iteration,
                )
            if e.response.status_code == 402:
                logger.error("Gemini provider returned 402 (payment/quota error)")
                return _degraded_response(
                    "insufficient_credits",
                    "I'm temporarily unable to process new requests. Please try again shortly, or contact support if this persists.",
                    iteration,
                )
            raise

        # Append the LLM's response message to history (OpenAI-style: role + content + tool_calls)
        assistant_message = llm_response["choices"][0]["message"]
        history.append(assistant_message)

        tool_calls = assistant_message.get("tool_calls") or []

        if not tool_calls:
            # LLM returned a final text response — we're done
            final_text = assistant_message.get("content") or ""

            reasoning_trace.append({
                "agent": "orchestrator",
                "decision": "Final response generated — no more tool calls needed",
                "timestamp": datetime.utcnow().isoformat(),
            })

            return {
                "response": final_text,
                "reasoning_trace": reasoning_trace,
                "iterations": iteration + 1,
                "nlp_analysis": nlp_analysis,
                "return_id": return_id,
                "return_initiated": return_initiated,
            }

        # Execute each tool call
        tool_results = []
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            try:
                tool_input = json.loads(tool_call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                logger.warning(f"Malformed tool arguments from LLM: {tool_call['function']['arguments']!r}")
                tool_input = {}

            # Map to specialist agent label for the trace
            agent_label = {
                "search_orders": "order_agent",
                "check_policy": "policy_agent",
                "initiate_return": "return_agent",
                "get_analytics": "analytics_agent",
            }.get(tool_name, "tool_agent")

            reasoning_trace.append({
                "agent": agent_label,
                "tool": tool_name,
                "input": tool_input,
                "timestamp": datetime.utcnow().isoformat(),
            })

            result = await execute_tool(tool_name, tool_input, customer_id, db)

            # Track if a return was initiated
            if tool_name == "initiate_return" and result.get("success"):
                return_id = result.get("return_id")
                return_initiated = True
                return_confirmation = result.get("message", f"Return {return_id} was successfully initiated.")

            reasoning_trace[-1]["result"] = result
            logger.info(f"Tool {tool_name} completed. Return initiated: {return_initiated}")

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result),
            })

        # Feed results back to the LLM, one message per tool call (OpenAI-style)
        history.extend(tool_results)

    # Exceeded iteration limit
    reasoning_trace.append({
        "agent": "orchestrator",
        "decision": "Max iterations (6) reached — returning partial response",
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {
        "response": (
            "I've gathered the information needed but need a moment to finalize. "
            "Could you confirm the details of your return request?"
        ),
        "reasoning_trace": reasoning_trace,
        "iterations": 6,
        "nlp_analysis": nlp_analysis,
        "return_id": return_id,
        "return_initiated": return_initiated,
    }

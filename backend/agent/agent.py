"""Claude tool-use orchestration loop for the YTIP chat agent.

Takes a user message + conversation history, runs a multi-turn tool-use loop
with Claude, and returns the final text response plus any widget specs created.

The loop:
  1. Send messages to Claude with tool definitions
  2. If Claude responds with tool_use blocks, execute them and feed results back
  3. Repeat until Claude returns a final text response or we hit MAX_ITERATIONS
"""

import json
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

import anthropic

from config import settings
from agent.system_prompt import build_system_prompt
from agent.tools import TOOL_DEFINITIONS, execute_tool
from agent.widget_schema import WidgetSpec

logger = logging.getLogger("ytip.agent")

# Sonnet for speed + quality balance on analytical queries
MODEL = "claude-sonnet-4-6-20250514"
MAX_TOKENS = 4096
MAX_ITERATIONS = 8


def run_agent(
    message: str,
    restaurant_id: int,
    restaurant_name: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Run the Claude agent with tool use.

    Args:
        message: The user's current message.
        restaurant_id: Tenant restaurant ID for query filtering.
        restaurant_name: Human-readable name for the system prompt.
        conversation_history: Previous messages in Anthropic API format
            (list of {"role": ..., "content": ...} dicts). Optional.

    Returns:
        Tuple of (text_response, list_of_widget_spec_dicts).
        Widget specs are serializable dicts matching WidgetSpec schema.
    """

    client = _get_client()
    if client is None:
        return (
            "The AI service is not configured. Please set the ANTHROPIC_API_KEY "
            "environment variable.",
            [],
        )

    system_prompt = build_system_prompt(restaurant_name, restaurant_id)

    # Build message list: history + new user message
    messages: List[Dict[str, Any]] = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": message})

    widgets: List[Dict[str, Any]] = []
    text_parts: List[str] = []

    for iteration in range(MAX_ITERATIONS):
        logger.info(
            "Agent iteration %d/%d for restaurant %d",
            iteration + 1,
            MAX_ITERATIONS,
            restaurant_id,
        )

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except anthropic.AuthenticationError:
            logger.error("Anthropic API authentication failed — check API key")
            return "AI service authentication failed. Please check the API key.", widgets
        except anthropic.RateLimitError:
            logger.warning("Anthropic API rate limited")
            return (
                "The AI service is temporarily rate-limited. Please try again "
                "in a minute.",
                widgets,
            )
        except anthropic.APIError as exc:
            logger.error("Anthropic API error: %s", exc)
            return (
                "I encountered an error connecting to the AI service. "
                "Please try again.",
                widgets,
            )

        # Separate text blocks from tool_use blocks
        text_parts_this_turn: List[str] = []
        tool_use_blocks: List[Any] = []

        for block in response.content:
            if block.type == "text":
                text_parts_this_turn.append(block.text)
            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        # Accumulate text from all turns
        text_parts.extend(text_parts_this_turn)

        # If Claude returned no tool calls, we're done
        if not tool_use_blocks:
            final_text = "\n".join(text_parts).strip()
            if not final_text:
                final_text = "I couldn't generate a response. Please try rephrasing."
            return final_text, widgets

        # Claude wants to use tools — add its response to message history
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool and collect results
        tool_results: List[Dict[str, Any]] = []
        for tool_block in tool_use_blocks:
            logger.info(
                "Executing tool: %s | Input keys: %s",
                tool_block.name,
                list(tool_block.input.keys()) if isinstance(tool_block.input, dict) else "N/A",
            )

            result = execute_tool(
                tool_block.name,
                tool_block.input,
                restaurant_id,
            )

            # Collect widgets from successful create_widget calls
            if tool_block.name == "create_widget" and "widget" in result:
                widgets.append(result["widget"])

            # Log errors for debugging
            if "error" in result:
                logger.warning(
                    "Tool %s returned error: %s",
                    tool_block.name,
                    result["error"],
                )

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": json.dumps(result, default=str),
            })

        # Feed tool results back to Claude as a user message
        messages.append({"role": "user", "content": tool_results})

    # Exhausted iterations — return whatever text we have
    logger.warning(
        "Agent hit MAX_ITERATIONS (%d) for restaurant %d",
        MAX_ITERATIONS,
        restaurant_id,
    )
    final_text = "\n".join(text_parts).strip()
    if not final_text:
        final_text = (
            "I ran out of processing steps. Your question may be too complex — "
            "try breaking it into smaller questions."
        )
    return final_text, widgets


# -------------------------------------------------------------------------
# Client singleton — thread-safe, avoids recreating on every request
# -------------------------------------------------------------------------
_client_lock = threading.Lock()
_client_instance: Optional[anthropic.Anthropic] = None


def _get_client() -> Optional[anthropic.Anthropic]:
    """Return a cached Anthropic client, or None if no API key is set."""

    global _client_instance
    if _client_instance is not None:
        return _client_instance

    with _client_lock:
        # Double-check inside lock to avoid race condition
        if _client_instance is not None:
            return _client_instance

        if not settings.anthropic_api_key:
            logger.error("ANTHROPIC_API_KEY not set — agent is disabled")
            return None

        _client_instance = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return _client_instance

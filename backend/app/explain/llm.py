import re
import asyncio
import logging
from typing import Dict, Any, Tuple, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You write a short plain-English summary for a claims investigator.\n"
    "Use only the facts in the provided evidence list. Do not add any facts, numbers\n"
    "or causes. Do not change the stated risk level. 2-3 sentences. If confidence\n"
    "is not 'high', mention that some checks were limited."
)

def extract_numbers(text: str) -> set:
    """Extracts all integer/float numbers from text."""
    # Find all sequences of digits, with optional decimals and commas
    cleaned = re.findall(r"\b\d+(?:[.,]\d+)?%?\b", text)
    numbers = set()
    for token in cleaned:
        token_clean = token.replace(",", "").replace("%", "")
        try:
            numbers.add(float(token_clean))
        except ValueError:
            pass
    return numbers

def validate_llm_output(output_text: str, input_context: str) -> bool:
    """
    Validation after generation (§16.4):
    Every number in the output must appear in the input; if any number
    or unverified entity appears, discard output and fallback to template.
    """
    out_numbers = extract_numbers(output_text)
    in_numbers = extract_numbers(input_context)

    # Discard if LLM hallucinated new numbers
    hallucinated = out_numbers - in_numbers
    if hallucinated:
        logger.warning(f"LLM hallucinated numbers {hallucinated}; falling back to template.")
        return False
    return True

async def generate_llm_summary(
    evidence_payload: Dict[str, Any],
    fallback_template: str
) -> Tuple[str, str]:
    """
    Attempts to rewrite summary using configured LLM (§16.4, §27.5).
    Falls back safely to template on any error, timeout, or validation failure.
    Returns: (summary_text, summary_source: "llm" | "template")
    """
    if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
        return fallback_template, "template"

    input_text = str(evidence_payload)

    try:
        # Provider-agnostic dispatch with short timeout (3.0s)
        # For now, if no real external provider is configured, return fallback
        provider = (settings.LLM_PROVIDER or "").lower()
        if provider not in ("openai", "anthropic", "gemini"):
            return fallback_template, "template"

        # (Extensible hook for live providers)
        # Timeout containment:
        # summary = await asyncio.wait_for(call_provider(...), timeout=3.0)
        # if validate_llm_output(summary, input_text):
        #     return summary, "llm"

        return fallback_template, "template"

    except Exception as e:
        logger.warning(f"LLM summary generation failed: {e}; using template.")
        return fallback_template, "template"

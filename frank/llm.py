"""
DeepSeek LLM integration for Frank.

Provides LLM-powered intent parsing as a superior alternative to
keyword-based matching. Uses the OpenAI-compatible DeepSeek API.

API credentials are read from ~/.frank/config.json (never from
environment variables or source code).
"""

import json
import os
from typing import Optional


def _load_config() -> dict:
    """Load Frank configuration from ~/.frank/config.json."""
    config_path = os.path.expanduser("~/.frank/config.json")
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def get_api_key() -> Optional[str]:
    """Return the DeepSeek API key from config, or None if not configured."""
    config = _load_config()
    return config.get("deepseek_api_key")


def get_model_name() -> str:
    """Return the configured DeepSeek model name."""
    config = _load_config()
    return config.get("deepseek_model", "deepseek-chat")


def get_base_url() -> str:
    """Return the DeepSeek API base URL."""
    config = _load_config()
    return config.get("deepseek_base_url", "https://api.deepseek.com")


def is_configured() -> bool:
    """Check whether the DeepSeek API key is configured."""
    key = get_api_key()
    return key is not None and len(key) > 0


INTENT_SYSTEM_PROMPT = """You are a computational chemistry intent parser. Your task is to extract structured parameters from a user's natural language description of a quantum chemistry calculation.

Return a JSON object with these fields (use null for missing fields):
- molecule: The molecule name, formula, or identifier (e.g., "h2o", "benzene", "caffeine")
- method: The computational method (e.g., "HF", "B3LYP", "PBE0", "MP2", "CCSD(T)", "wB97X-D", "M06-2X")
- basis: The basis set (e.g., "6-31G*", "cc-pVDZ", "cc-pVTZ", "def2-TZVP", "STO-3G")
- calc_type: The calculation type, one of: "energy", "geometry", "frequency", "excited", "casscf", "nbo", "solvation"
- solvent: The solvent name if solvation is requested (e.g., "water", "ethanol", "dmso", "acetone")
- n_states: Number of excited states if TDDFT/excited calculation (integer)
- norb: Number of active orbitals if CASSCF (integer)
- nelec: Number of active electrons if CASSCF (integer)
- accuracy: Desired accuracy level, one of: "low", "medium", "high"
- confidence: Your confidence in the parsed result (0.0 to 1.0)

Rules:
1. If the user asks to "calculate energy" or "compute energy" or "单点能", calc_type is "energy"
2. If the user asks for "optimization", "优化", "几何优化", calc_type is "geometry"
3. If the user asks for "frequency", "频率", "振动", "热力学", calc_type is "frequency"
4. If the user asks for "excited", "激发态", "TDDFT", "光谱", "UV-Vis", calc_type is "excited"
5. If the user specifies a method, extract it exactly as given (case-insensitive match to the canonical name)
6. If no method is specified, leave it null
7. Default to Chinese molecule names (水=h2o, 苯=c6h6, 乙醇=c2h5oh, 甲醇=ch3oh, 氨=nh3, 甲烷=ch4, 乙烯=c2h4, 乙炔=c2h2, 甲醛=h2co, 乙酸=ch3cooh, 丙酮=ch3coch3)
8. Chinese or English input are both accepted
9. Output ONLY the JSON object, no other text."""


def parse_intent_with_llm(text: str) -> Optional[dict]:
    """Use DeepSeek LLM to parse the user's computational chemistry intent.

    Args:
        text: The user's natural language query.

    Returns:
        A dict with parsed intent fields, or None if LLM is unavailable
        or the call fails.
    """
    if not is_configured():
        return None

    api_key = get_api_key()
    base_url = get_base_url()
    model = get_model_name()

    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Normalize field names
        normalized = {
            "molecule": result.get("molecule"),
            "method": result.get("method"),
            "basis": result.get("basis"),
            "calc_type": result.get("calc_type"),
            "solvent": result.get("solvent"),
            "n_states": result.get("n_states"),
            "norb": result.get("norb"),
            "nelec": result.get("nelec"),
            "accuracy": result.get("accuracy", "medium"),
            "confidence": float(result.get("confidence", 0.5)),
        }

        # Convert n_states/norb/nelec to int if present
        for key in ("n_states", "norb", "nelec"):
            if normalized[key] is not None:
                try:
                    normalized[key] = int(normalized[key])
                except (ValueError, TypeError):
                    normalized[key] = None

        return normalized

    except Exception:
        return None


def chat_reply_with_llm(user_text: str, conversation_history: list[dict] = None) -> Optional[str]:
    """Generate a natural conversational reply using the LLM.

    Used for non-chemistry chat (greetings, questions, emotional expressions,
    general conversation) to make interactions feel human rather than robotic.

    Args:
        user_text: The user's message.
        conversation_history: Optional list of prior messages as {"role": "...", "content": "..."}.

    Returns:
        A conversational reply string, or None if LLM is unavailable.
    """
    if not is_configured():
        return None

    api_key = get_api_key()
    base_url = get_base_url()
    model = get_model_name()

    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=api_key, base_url=base_url)

    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history[-6:])  # Keep last 6 turns for context
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def test_connection() -> tuple[bool, str]:
    """Test the DeepSeek API connection.

    Returns:
        Tuple of (success, message).
    """
    if not is_configured():
        return False, "API key not configured"

    api_key = get_api_key()
    base_url = get_base_url()
    model = get_model_name()

    try:
        from openai import OpenAI
    except ImportError:
        return False, "openai package not installed"

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with just: OK"}],
            max_tokens=10,
        )
        return True, f"Connection successful (model: {model})"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


CHAT_SYSTEM_PROMPT = """You are Frank, a friendly and knowledgeable computational chemistry assistant running in a terminal. You help users with quantum chemistry calculations using natural language.

Your personality:
- Warm and approachable, like a helpful lab colleague
- Genuinely interested in chemistry and the user's research questions
- When a user expresses frustration, confusion, or negative emotions, respond with empathy first, then offer help
- Use plain language to explain concepts; avoid unnecessary jargon unless the user is clearly an expert
- Keep responses concise (2-5 sentences) since this is a terminal interface
- If the user says something unrelated to chemistry, gently acknowledge it and steer back to what you can help with
- Use the same language as the user (Chinese for Chinese input, English for English input)
- NEVER use emoji or emoticons in your responses — this is a professional terminal application

What you can do:
- Parse computational chemistry requests and generate PySCF code
- Execute calculations (HF, DFT, MP2, CCSD(T), TDDFT, CASSCF, and more)
- Help with basis set selection, method recommendations, and workflow design
- Search PubChem for molecules
- Import XYZ files
- Run multi-step workflows: geometry optimization + frequency, method comparison, basis set convergence, PES scan, solvation free energy

If the user seems new, suggest they start with something simple like "calculate the energy of water"."""

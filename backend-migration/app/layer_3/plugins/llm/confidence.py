from __future__ import annotations

import re
from typing import Any


# Ranking weight for README values inferred by the LLM. This is the source
# reliability shown on the extracted result. It is separate from the model's
# own confidence score.
LLM_SOURCE_RELIABILITY = 0.7

_TOKEN = re.compile(r"[a-z0-9]+")
_MARKDOWN = re.compile(r"[*_`>#]")
_WHITESPACE = re.compile(r"\s+")


def normalize_confidence(value: Any, default: float = 0.0) -> float:
    """Convert a model confidence score to a float in ``[0, 1]``.

    A list of scores, which list-valued properties sometimes return, is averaged.
    """
    if isinstance(value, list):
        scores = [normalize_confidence(item, default) for item in value]
        if not scores:
            return float(default)
        return max(0.0, min(1.0, sum(scores) / len(scores)))
    try:
        confidence = float(value)
    except Exception:
        confidence = float(default)
    if confidence != confidence:  # NaN
        confidence = float(default)
    return max(0.0, min(1.0, confidence))


def evidence_quotes(evidence: Any) -> list[str]:
    """Collect quote strings from a string, a list of quotes, or a mapping of quotes."""
    if isinstance(evidence, str):
        text = evidence.strip()
        return [text] if text else []
    if isinstance(evidence, list):
        quotes: list[str] = []
        for item in evidence:
            quotes.extend(evidence_quotes(item))
        return quotes
    if isinstance(evidence, dict):
        for key in ("evidence", "quote", "text"):
            if key in evidence:
                return evidence_quotes(evidence[key])
        quotes = []
        for item in evidence.values():
            quotes.extend(evidence_quotes(item))
        return quotes
    return []


def format_evidence(evidence: Any) -> str | None:
    """Return the model's evidence quotes as one string, or ``None`` when absent."""
    quotes = evidence_quotes(evidence)
    return "\n".join(quotes) or None


def _plain(text: str) -> str:
    return _WHITESPACE.sub(" ", _MARKDOWN.sub("", text)).strip().casefold()


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.casefold())


def _sentences(source_text: str) -> list[str]:
    sentences: list[str] = []
    for block in re.split(r"\n+", source_text or ""):
        block = block.strip()
        if not block:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", block):
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)
    return sentences


def _states_value(sentence: str, item: str) -> bool:
    """True when the sentence states the value, not merely an overlapping substring."""
    sentence_plain = _plain(sentence)
    item_plain = _plain(item)
    if not item_plain or not sentence_plain:
        return False
    if " " in item_plain:
        return item_plain in sentence_plain
    return re.search(rf"\b{re.escape(item_plain)}\b", sentence_plain) is not None


def _is_url_mention(sentence: str) -> bool:
    return bool(re.search(r"https?://|(?:^|[\s|(])/[\w.-]+", sentence, flags=re.IGNORECASE))


def _best_support(item: str, candidates: list[str]) -> str | None:
    matches = [candidate for candidate in candidates if _states_value(candidate, item)]
    if not matches:
        return None
    return min(matches, key=lambda text: (_is_url_mention(text), len(_tokens(text)), len(text)))


# Labels, aliases, names, and URLs are copied from the README, so a quote that
# does not state them can be replaced. Description and intended use are paraphrases.
_LITERAL_QUOTE_PROPERTIES = {
    "alternateNames",
    "applicationCategory",
    "buildInstructions",
    "contact",
    "installation",
    "name",
}
_PARAPHRASE_PROPERTIES = {"description", "intendedUse"}


def supporting_evidence(
    value: Any,
    evidence: Any,
    source_text: str,
    property_name: str | None = None,
) -> str | None:
    """Use quotes that state literal values, searching the README when the model cites something else.

    ``description`` and ``intendedUse`` keep the model's quote. Their values are
    paraphrases, so a sentence search would not raise confidence honestly.
    """
    original = format_evidence(evidence)
    if property_name in _PARAPHRASE_PROPERTIES:
        return original
    if isinstance(value, list):
        items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    elif isinstance(value, str) and value.strip() and property_name in _LITERAL_QUOTE_PROPERTIES:
        items = [value.strip()]
    elif isinstance(value, str) and value.strip():
        if original and _plain(original) in _plain(source_text or ""):
            return original
        items = [value.strip()]
    else:
        return original

    source_plain = _plain(source_text or "")
    model_quotes = [
        quote for quote in evidence_quotes(evidence) if _plain(quote) in source_plain
    ]
    sentences = _sentences(source_text)
    chosen: list[str] = []
    for item in items:
        quote = _best_support(item, model_quotes) or _best_support(item, sentences)
        if quote:
            chosen.append(quote.strip())
    if chosen:
        return "\n".join(dict.fromkeys(chosen))
    return original


def _value_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(item for item in value if isinstance(item, str))
    if value is None:
        return ""
    return str(value)


def _quote_parts(evidence: Any) -> list[str]:
    """Split stored evidence into the sentences that were joined for display."""
    parts: list[str] = []
    for quote in evidence_quotes(evidence):
        parts.extend(line.strip() for line in quote.splitlines() if line.strip())
    return parts


def _value_items(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _stated_sentence_confidence(item: str, sentence: str) -> float:
    """Score one README sentence that states one value, without the model's old prior."""
    item_tokens = _tokens(item)
    sentence_tokens = _tokens(sentence)
    if not item_tokens or not sentence_tokens:
        return 0.0
    specificity = min(1.0, (len(item_tokens) * 3) / len(sentence_tokens))
    return 0.55 + 0.45 * specificity


def confidence_from_evidence(
    model_confidence: Any,
    value: Any,
    evidence: Any,
    source_text: str,
) -> float:
    """Score how directly the cited evidence states the extracted value.

    The model's own number is only a prior. A quote that merely mentions the
    value inside a long passage cannot stay at 1, and a quote that is not in
    the README cannot keep the model's score. Separate supporting sentences are
    scored on their own: joined together, they are not one contiguous README span.
    """
    reported = normalize_confidence(model_confidence)
    quotes = _quote_parts(evidence)
    if not quotes:
        return 0.0
    source_plain = _plain(source_text or "")
    grounded = [quote for quote in quotes if _plain(quote) in source_plain]
    if not grounded:
        return round(min(reported * 0.25, 0.25), 2)

    items = _value_items(value)
    supports = [_best_support(item, grounded) for item in items]
    if items and all(supports):
        scores = [
            _stated_sentence_confidence(item, sentence)
            for item, sentence in zip(items, supports)
        ]
        return round(sum(scores) / len(scores), 2)

    quote = "\n".join(grounded)
    value_tokens = _tokens(_value_text(value))
    evidence_tokens = _tokens(quote)
    if not value_tokens or not evidence_tokens:
        return 0.0

    evidence_vocabulary = set(evidence_tokens)
    support = sum(token in evidence_vocabulary for token in value_tokens) / len(value_tokens)
    specificity = min(1.0, (len(value_tokens) * 3) / len(evidence_tokens))
    evidence_score = support * (0.55 + 0.45 * specificity)
    return round(normalize_confidence(reported * evidence_score), 2)
import re
import unicodedata
from typing import Optional, Set
from rapidfuzz import fuzz, process


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower().strip()

    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def find_closest_make(
    user_input: str,
    known_makes: Set[str],
    threshold: int = 70,
) -> Optional[str]:
    if not user_input or not known_makes:
        return None

    normalized_input = normalize_text(user_input)

    normalized_known = {normalize_text(m): m for m in known_makes}
    if normalized_input in normalized_known:
        return normalized_known[normalized_input]

    best_match = process.extractOne(
        normalized_input,
        list(normalized_known.keys()),
        scorer=fuzz.ratio,
        score_cutoff=threshold,
    )

    if best_match:
        return normalized_known[best_match[0]]

    return None


def find_closest_model(
    user_input: str,
    known_models: Set[str],
    threshold: int = 70,
) -> Optional[str]:
    if not user_input or not known_models:
        return None

    normalized_input = normalize_text(user_input)

    normalized_known = {normalize_text(m): m for m in known_models}
    if normalized_input in normalized_known:
        return normalized_known[normalized_input]

    best_match = process.extractOne(
        normalized_input,
        list(normalized_known.keys()),
        scorer=fuzz.ratio,
        score_cutoff=threshold,
    )

    if best_match:
        return normalized_known[best_match[0]]

    return None

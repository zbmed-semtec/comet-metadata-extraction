from dataclasses import dataclass
from typing import List, Optional
import spdx_matcher


@dataclass
class License:
    name: str
    spdx_id: str


@dataclass
class LicenseMatch:
    license: License
    confidence: float


def match_spdx_license(text: str, fuzzy_threshold: float = 0.8) -> list[LicenseMatch]:
    """
    Identifies licenses within the given text using `spdx_matcher`.

    The function first attempts an exact match. If no exact match is found,
    it falls back to fuzzy matching (requires `pip install spdx_matcher[fuzzy]`).

    :param text: Raw license text to analyze.
    :param fuzzy_threshold: Minimum similarity threshold (0.0 - 1.0) for fuzzy matching.
    :return: A list of LicenseMatch instances.
    """
    if not text or not text.strip():
        return []

    results: list[LicenseMatch] = []

    # 1. Attempt exact match
    try:
        analysis, _ = spdx_matcher.analyse_license_text(text)
        if isinstance(analysis, dict):
            # Handles both "license" and "licenses" keys depending on the library version
            detected_licenses = analysis.get("license") or analysis.get("licenses") or {}

            for spdx_id in detected_licenses.keys():
                results.append(
                    LicenseMatch(
                        license=License(name=spdx_id, spdx_id=spdx_id),
                        confidence=1.0,
                    )
                )
    except Exception:
        # Pass through to fuzzy matching if exact analysis fails or errors
        pass

    # If exact matches were found, return them
    if results:
        return results

    # 2. Fall back to fuzzy match if no exact match was detected
    try:
        fuzzy_matches = spdx_matcher.fuzzy_license_text(text, threshold=fuzzy_threshold)
        if fuzzy_matches:
            for match in fuzzy_matches:
                # Filter specifically for licenses (exclude exception identifiers)
                if match.get("type", "license") == "license":
                    spdx_id = match.get("id")
                    score = float(match.get("score", 0.0))
                    
                    if spdx_id:
                        results.append(
                            LicenseMatch(
                                license=License(name=spdx_id, spdx_id=spdx_id),
                                confidence=score,
                            )
                        )

            # Sort results by confidence descending
            results.sort(key=lambda m: m.confidence, reverse=True)
    except (AttributeError, NotImplementedError, Exception):
        # Gracefully handle situations where fuzzy dependencies (like jellyfish)
        # are not installed or the input cannot be processed
        pass

    return results
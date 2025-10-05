from difflib import SequenceMatcher


class FuzzyMatcher:
    @staticmethod
    def similarity(str1: str, str2: str) -> float:
        """Return similarity score between 0 and 1"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    @staticmethod
    def is_match(str1: str, str2: str, threshold: float = 0.85) -> bool:
        """Check if two strings are fuzzy matches"""
        return FuzzyMatcher.similarity(str1, str2) >= threshold

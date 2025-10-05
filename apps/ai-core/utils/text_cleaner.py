import re


class TextCleaner:
    @staticmethod
    def clean(text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove markdown artifacts
        text = re.sub(r"\*\*", "", text)
        text = re.sub(r"__", "", text)

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace("'", "'").replace("'", "'")

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

import tiktoken
from typing import List, Dict
import hashlib


class Chunker:
    def __init__(self, target_tokens: int = 500, overlap_tokens: int = 50):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str) -> List[Dict]:
        """Split text into chunks with overlap"""
        # Split on paragraphs first
        paragraphs = text.split("\n\n")

        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = len(self.encoding.encode(para))

            if current_tokens + para_tokens > self.target_tokens and current_chunk:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "token_count": current_tokens,
                        "hash": hashlib.sha256(chunk_text.encode()).hexdigest(),
                    }
                )

                # Start new chunk with overlap
                current_chunk = (
                    current_chunk[-1:] if current_chunk else []
                )  # Keep last paragraph for overlap
                current_tokens = (
                    len(self.encoding.encode(current_chunk[0])) if current_chunk else 0
                )

            current_chunk.append(para)
            current_tokens += para_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "token_count": current_tokens,
                    "hash": hashlib.sha256(chunk_text.encode()).hexdigest(),
                }
            )

        return chunks

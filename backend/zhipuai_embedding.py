import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
import zhipuai
from typing import List, Optional


class ZhipuAIEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Custom ChromaDB embedding function using ZhipuAI API.
    """

    def __init__(self, api_key: str, model: str = "embedding-3"):
        """
        Initialize the ZhipuAI embedding function.

        Args:
            api_key: ZhipuAI API key
            model: Model name to use for embeddings
        """
        if not api_key:
            raise ValueError("ZhipuAI API key is required")

        self.client = zhipuai.ZhipuAI(api_key=api_key)
        self.model = model

    def __call__(self, texts: Documents) -> Embeddings:
        """
        Generate embeddings for the given texts using ZhipuAI API.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []

        # Process texts in batches to avoid timeout
        for i, text in enumerate(texts):
            try:
                print(f"Generating embedding {i+1}/{len(texts)}...")

                # Call ZhipuAI embedding API with timeout
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    timeout=30  # 30 second timeout
                )

                # Extract embedding from response
                if response and hasattr(response, 'data') and len(response.data) > 0:
                    embedding = response.data[0].embedding
                    embeddings.append(embedding)
                    print(f"  ✓ Success (dimension: {len(embedding)})")
                else:
                    raise Exception(f"Invalid response from ZhipuAI: {response}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                # Return zero vector as fallback (assuming 1024 dimensions for embedding-2)
                embeddings.append([0.0] * 1024)

        return embeddings


def create_zhipuai_embedding_function(api_key: str, model: str = "embedding-3") -> ZhipuAIEmbeddingFunction:
    """
    Factory function to create a ZhipuAI embedding function.

    Args:
        api_key: ZhipuAI API key
        model: Model name to use for embeddings

    Returns:
        ZhipuAIEmbeddingFunction instance
    """
    return ZhipuAIEmbeddingFunction(api_key=api_key, model=model)

"""Tests for EmbeddingsService"""
import pytest
from services.embeddings import EmbeddingsService
from unittest.mock import Mock, patch


def test_embeddings_service_initialization():
    """Test EmbeddingsService initializes with correct model info"""
    service = EmbeddingsService()

    assert service.model == "text-embedding-3-small"
    assert service.dimensions == 1536


def test_get_model_info():
    """Test get_model_info returns correct information"""
    service = EmbeddingsService()
    info = service.get_model_info()

    assert info["model"] == "text-embedding-3-small"
    assert info["dimensions"] == 1536
    assert info["provider"] == "OpenAI"


def test_generate_embedding_empty_text():
    """Test generate_embedding handles empty text gracefully"""
    service = EmbeddingsService()

    # Should return zero vector for empty text
    embedding = service.generate_embedding("")

    assert len(embedding) == 1536
    assert all(v == 0.0 for v in embedding)


def test_generate_embeddings_batch_empty_list():
    """Test generate_embeddings_batch handles empty list"""
    service = EmbeddingsService()

    embeddings = service.generate_embeddings_batch([])

    assert embeddings == []


def test_generate_embeddings_batch_all_empty_texts():
    """Test generate_embeddings_batch handles all empty texts"""
    service = EmbeddingsService()

    embeddings = service.generate_embeddings_batch(["", "  ", "\n"])

    assert len(embeddings) == 3
    assert all(len(emb) == 1536 for emb in embeddings)


@patch('services.embeddings.OpenAI')
def test_generate_embedding_success(mock_openai):
    """Test successful single embedding generation"""
    # Mock OpenAI response
    mock_client = Mock()
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create.return_value = mock_response
    mock_openai.return_value = mock_client

    service = EmbeddingsService()
    embedding = service.generate_embedding("This is a test sentence.")

    assert len(embedding) == 1536
    assert all(isinstance(v, float) for v in embedding)
    mock_client.embeddings.create.assert_called_once()


@patch('services.embeddings.OpenAI')
def test_generate_embeddings_batch_success(mock_openai):
    """Test successful batch embedding generation"""
    # Mock OpenAI response
    mock_client = Mock()
    mock_response = Mock()
    mock_response.data = [
        Mock(embedding=[0.1] * 1536),
        Mock(embedding=[0.2] * 1536),
        Mock(embedding=[0.3] * 1536)
    ]
    mock_client.embeddings.create.return_value = mock_response
    mock_openai.return_value = mock_client

    service = EmbeddingsService()
    texts = [
        "First sentence.",
        "Second sentence.",
        "Third sentence."
    ]
    embeddings = service.generate_embeddings_batch(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 1536 for emb in embeddings)
    mock_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input=texts
    )


@patch('services.embeddings.OpenAI')
def test_generate_embedding_api_error(mock_openai):
    """Test handling of API errors"""
    # Mock OpenAI to raise an exception
    mock_client = Mock()
    mock_client.embeddings.create.side_effect = Exception("API Error")
    mock_openai.return_value = mock_client

    service = EmbeddingsService()

    with pytest.raises(Exception) as exc_info:
        service.generate_embedding("Test text")

    assert "API Error" in str(exc_info.value)


@patch('services.embeddings.OpenAI')
def test_generate_embeddings_batch_filters_empty(mock_openai):
    """Test batch generation filters out empty texts before API call"""
    # Mock OpenAI response
    mock_client = Mock()
    mock_response = Mock()
    mock_response.data = [
        Mock(embedding=[0.1] * 1536),
        Mock(embedding=[0.2] * 1536)
    ]
    mock_client.embeddings.create.return_value = mock_response
    mock_openai.return_value = mock_client

    service = EmbeddingsService()
    texts = [
        "First sentence.",
        "",  # Empty
        "Second sentence.",
        "   "  # Whitespace only
    ]
    embeddings = service.generate_embeddings_batch(texts)

    # Should only call API with non-empty texts
    call_args = mock_client.embeddings.create.call_args
    assert len(call_args.kwargs['input']) == 2
    assert call_args.kwargs['input'][0] == "First sentence."
    assert call_args.kwargs['input'][1] == "Second sentence."


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

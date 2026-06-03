"""Tests for knowledge providers: Reranker and WebSearchTool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwps_agent_api.knowledge.reranker import Reranker
from pwps_agent_api.schemas import KnowledgeHit, SourceType


@pytest.fixture
def sample_hits() -> list[KnowledgeHit]:
    return [
        KnowledgeHit(
            source_type=SourceType.LOCAL_DOCUMENT,
            source_id="doc-1",
            title="GMAW Reference",
            source_ref="local://gmaw",
            section_path=["GMAW", "Consumables"],
            content="ER50-6 is standard wire for carbon steel GMAW.",
            target_fields=["consumable"],
            score=0.8,
            limitations="Reference only.",
        ),
        KnowledgeHit(
            source_type=SourceType.LOCAL_DOCUMENT,
            source_id="doc-2",
            title="Thermal Requirements",
            source_ref="local://thermal",
            section_path=["Thermal"],
            content="Preheat temperature depends on material and thickness.",
            target_fields=["preheat_temperature"],
            score=0.7,
            limitations="General guidance.",
        ),
    ]


class TestReranker:
    async def test_rerank_returns_empty_for_empty_hits(self) -> None:
        reranker = Reranker()
        result = await reranker.rerank("test query", [])
        assert result == []

    async def test_rerank_returns_original_order_without_api_key(
        self, sample_hits: list[KnowledgeHit]
    ) -> None:
        reranker = Reranker(top_n=2)
        with patch("pwps_agent_api.knowledge.reranker.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(reranker_api_key="")
            result = await reranker.rerank("test query", sample_hits)

        assert len(result) == 2
        assert result[0].source_id == "doc-1"
        assert result[1].source_id == "doc-2"

    async def test_rerank_limits_results_to_top_n(self, sample_hits: list[KnowledgeHit]) -> None:
        reranker = Reranker(top_n=1)
        with patch("pwps_agent_api.knowledge.reranker.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(reranker_api_key="")
            result = await reranker.rerank("test query", sample_hits)

        assert len(result) == 1

    async def test_rerank_calls_api_with_correct_parameters(
        self, sample_hits: list[KnowledgeHit]
    ) -> None:
        reranker = Reranker(top_n=2)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"index": 1, "relevance_score": 0.95},
                {"index": 0, "relevance_score": 0.85},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("pwps_agent_api.knowledge.reranker.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                reranker_api_key="test-key",
                reranker_base_url="https://api.test.com/v1",
                reranker_model="test-model",
            )
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(post=AsyncMock(return_value=mock_response))
                )
                mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

                result = await reranker.rerank("GMAW consumable", sample_hits)

        assert len(result) == 2
        # Results should be reordered: doc-2 first (index 1), then doc-1 (index 0)
        assert result[0].source_id == "doc-2"
        assert result[0].score == 0.95
        assert result[1].source_id == "doc-1"
        assert result[1].score == 0.85

    async def test_rerank_falls_back_to_original_order_on_api_error(
        self, sample_hits: list[KnowledgeHit]
    ) -> None:
        reranker = Reranker(top_n=2)

        with patch("pwps_agent_api.knowledge.reranker.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                reranker_api_key="test-key",
                reranker_base_url="https://api.test.com/v1",
                reranker_model="test-model",
            )
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__ = AsyncMock(
                    side_effect=Exception("Network error")
                )

                result = await reranker.rerank("test query", sample_hits)

        # Should fall back to original order
        assert len(result) == 2
        assert result[0].source_id == "doc-1"
        assert result[1].source_id == "doc-2"

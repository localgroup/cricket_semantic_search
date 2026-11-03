from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from rag.embeddings import BATCH_SIZE, DEFAULT_EMBEDDING_MODEL, get_embeddings
from rag.retrieval import _event_from_document, _qdrant_filter


class LangChainEmbeddingTests(SimpleTestCase):
    def setUp(self):
        get_embeddings.cache_clear()

    def tearDown(self):
        get_embeddings.cache_clear()

    @patch("rag.embeddings.HuggingFaceEmbeddings")
    def test_embeddings_use_configured_cpu_sentence_transformer(self, embedding_class):
        get_embeddings()

        embedding_class.assert_called_once_with(
            model_name=DEFAULT_EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"batch_size": BATCH_SIZE, "normalize_embeddings": True},
        )

    @patch("rag.embeddings.HuggingFaceEmbeddings")
    def test_embeddings_are_cached(self, embedding_class):
        self.assertIs(get_embeddings(), get_embeddings())
        embedding_class.assert_called_once()


class LangChainRetrievalTests(SimpleTestCase):
    def test_qdrant_filters_target_langchain_metadata(self):
        qdrant_filter = _qdrant_filter({"match_id": "MATCH001", "team": "Team B"})

        conditions = qdrant_filter.must
        self.assertEqual([condition.key for condition in conditions], ["metadata.match_id", "metadata.team"])

    def test_document_metadata_maps_to_api_event_shape(self):
        document = Mock(
            page_content="searchable cricket commentary",
            metadata={
                "event_id": "event-1",
                "match_id": "MATCH001",
                "event_type": "LBW given",
                "player": "Player 9",
                "team": "Team B",
                "commentary": "Decision reviewed.",
            },
        )

        event = _event_from_document(document, 0.987)

        self.assertEqual(event["event_id"], "event-1")
        self.assertEqual(event["score"], 0.987)
        self.assertEqual(event["search_text"], "searchable cricket commentary")

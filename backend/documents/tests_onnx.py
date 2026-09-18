from unittest.mock import Mock, patch

import numpy as np
from django.test import SimpleTestCase, override_settings

from .services.embeddings import OnnxEmbeddingProvider


class FakeEncoding:
    ids = [101, 42, 102]
    attention_mask = [1, 1, 1]
    type_ids = [0, 0, 0]


class OnnxEmbeddingProviderTests(SimpleTestCase):
    def tearDown(self):
        OnnxEmbeddingProvider._session = None
        OnnxEmbeddingProvider._tokenizer = None

    @override_settings(EMBEDDING_ONNX_BATCH_SIZE=2)
    def test_batches_mean_pools_and_normalizes(self):
        session = Mock()
        session.get_inputs.return_value = [Mock(name='input_ids'), Mock(name='attention_mask')]
        session.get_inputs.return_value[0].name = 'input_ids'
        session.get_inputs.return_value[1].name = 'attention_mask'
        session.run.side_effect = [
            [np.ones((2, 3, 384), dtype=np.float32)],
            [np.ones((1, 3, 384), dtype=np.float32)],
        ]
        tokenizer = Mock()
        tokenizer.encode_batch.side_effect = [
            [FakeEncoding(), FakeEncoding()],
            [FakeEncoding()],
        ]

        provider = OnnxEmbeddingProvider()
        with patch.object(provider, '_get_runtime', return_value=(session, tokenizer)):
            vectors = provider.embed_texts(['one', 'two', 'three'])

        self.assertEqual(len(vectors), 3)
        self.assertEqual(len(vectors[0]), 384)
        self.assertAlmostEqual(np.linalg.norm(vectors[0]), 1.0, places=6)
        self.assertEqual(session.run.call_count, 2)

    def test_empty_input_does_not_load_runtime(self):
        provider = OnnxEmbeddingProvider()
        with patch.object(provider, '_get_runtime') as load_runtime:
            self.assertEqual(provider.embed_texts([]), [])
        load_runtime.assert_not_called()

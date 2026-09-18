import json
import os
import sys
from pathlib import Path

import numpy as np


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django  # noqa: E402

django.setup()

from documents.services.embeddings import (  # noqa: E402
    OnnxEmbeddingProvider,
    SentenceTransformersEmbeddingProvider,
)


TEXTS = [
    'Semantic retrieval links a research question to evidence with related meaning.',
    'Café naïve résumé — 数据驱动的研究需要可验证的证据。',
    ' '.join(['Long-input truncation must match the established tokenizer behavior.'] * 100),
    (
        'Participants completed a randomized controlled trial comparing the intervention '
        'with usual care. The primary outcome was measured after twelve weeks, and the '
        'authors reported confidence intervals alongside the estimated treatment effect.'
    ),
    (
        'We evaluate dense retrieval on scientific abstracts. Mean-pooled transformer '
        'representations improve semantic recall when terminology differs between queries '
        'and source passages, although citation inspection remains necessary.'
    ),
]
QUERIES = [
    'How was the treatment evaluated?',
    'finding evidence when different words are used',
]


def cosine_matrix(left, right):
    return np.asarray(left) @ np.asarray(right).T


def main():
    reference = SentenceTransformersEmbeddingProvider().embed_texts(TEXTS + QUERIES)
    candidate = OnnxEmbeddingProvider().embed_texts(TEXTS + QUERIES)
    reference_array = np.asarray(reference)
    candidate_array = np.asarray(candidate)
    row_agreement = np.sum(reference_array * candidate_array, axis=1)

    corpus_count = len(TEXTS)
    reference_scores = cosine_matrix(reference_array[corpus_count:], reference_array[:corpus_count])
    candidate_scores = cosine_matrix(candidate_array[corpus_count:], candidate_array[:corpus_count])
    reference_rankings = np.argsort(-reference_scores, axis=1).tolist()
    candidate_rankings = np.argsort(-candidate_scores, axis=1).tolist()

    result = {
        'maximum_absolute_component_difference': float(np.max(np.abs(reference_array - candidate_array))),
        'mean_absolute_component_difference': float(np.mean(np.abs(reference_array - candidate_array))),
        'minimum_same_text_cosine_agreement': float(np.min(row_agreement)),
        'reference_rankings': reference_rankings,
        'onnx_rankings': candidate_rankings,
        'ranking_match': reference_rankings == candidate_rankings,
    }
    print(json.dumps(result, indent=2))

    compatible = (
        result['maximum_absolute_component_difference'] <= 1e-4
        and result['minimum_same_text_cosine_agreement'] >= 0.99999
        and result['ranking_match']
    )
    raise SystemExit(0 if compatible else 1)


if __name__ == '__main__':
    main()

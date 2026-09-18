import json
import gc
import os
import sys
import tempfile
import time
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def stage(name, action):
    started = time.perf_counter()
    value = action()
    print(json.dumps({'stage': name, 'seconds': time.perf_counter() - started}), flush=True)
    return value


def main():
    import django

    stage('django_setup', django.setup)
    from documents.services.chunking import chunk_pages
    from documents.services.embeddings import OnnxEmbeddingProvider
    from documents.services.extraction import extract_pdf_pages

    provider = OnnxEmbeddingProvider()
    stage('model_initialization', lambda: provider.embed_texts(['warmup']))
    long_texts = [' '.join(['academic evidence retrieval evaluation'] * 150)] * 8
    for index in range(3):
        stage(f'embedding_pass_{index + 1}', lambda: provider.embed_texts(long_texts))

    import fitz

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as stream:
        pdf_path = Path(stream.name)
    try:
        pdf = fitz.open()
        for page_number in range(150):
            page = pdf.new_page()
            text = ' '.join(
                [f'Page {page_number + 1} reports representative academic findings.'] * 80,
            )
            page.insert_textbox(page.rect + (36, 36, -36, -36), text, fontsize=9)
        figure_samples = os.urandom(1600 * 1600 * 3)
        figure = fitz.Pixmap(fitz.csRGB, 1600, 1600, figure_samples, False)
        pdf[0].insert_image(fitz.Rect(420, 650, 570, 800), pixmap=figure)
        pdf.save(pdf_path)
        pdf.close()
        del figure, figure_samples
        gc.collect()

        pages, _ = stage('pdf_extraction', lambda: extract_pdf_pages(pdf_path))
        chunks = stage('pdf_chunking', lambda: chunk_pages(pages, chunk_size=1000, overlap=200))
        print(json.dumps({
            'stage': 'pdf_workload',
            'seconds': 0,
            'pages': len(pages),
            'chunks': len(chunks),
            'pdf_bytes': pdf_path.stat().st_size,
        }), flush=True)
        stage('pdf_chunk_embedding', lambda: provider.embed_texts([item.content for item in chunks]))
        del pages, chunks
        stage('retained_after_cleanup', lambda: (gc.collect(), time.sleep(1)))
    finally:
        pdf_path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()

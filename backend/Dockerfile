FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENVIRONMENT=production \
    EMBEDDING_PROVIDER=onnx \
    EMBEDDING_ONNX_MODEL_PATH=/app/.models/minilm/model.onnx \
    EMBEDDING_ONNX_TOKENIZER_PATH=/app/.models/minilm/tokenizer.json \
    EMBEDDING_ONNX_BATCH_SIZE=8 \
    EMBEDDING_ONNX_INTRA_OP_THREADS=1 \
    EMBEDDING_ONNX_INTER_OP_THREADS=1

WORKDIR /app

COPY requirements-base.txt requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt

COPY embedding-artifacts.json ./
COPY tools/download_embedding_artifacts.py tools/download_embedding_artifacts.py
RUN python tools/download_embedding_artifacts.py /app/.models/minilm

COPY . .
RUN DJANGO_ENVIRONMENT=build python manage.py collectstatic --noinput \
    && chmod +x entrypoint.sh \
    && python -c "import importlib.util as i; assert i.find_spec('onnxruntime'); assert i.find_spec('tokenizers'); assert i.find_spec('torch') is None; assert i.find_spec('transformers') is None; assert i.find_spec('sentence_transformers') is None"

EXPOSE 10000
CMD ["./entrypoint.sh"]

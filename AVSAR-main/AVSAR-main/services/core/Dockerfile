# AVSAR core — Python 3.12 + FastAPI (TECH_STACK.md §1)
#
# Build arg WITH_ML (default 1) installs torch-CPU + sentence-transformers and
# **pre-downloads multilingual-e5-base into the image**. That matters for RULE 1:
# the build needs network (every docker build does), but once built the container
# embeds text with zero network and zero API keys. Set WITH_ML=0 for a fast,
# small image — core then uses the deterministic hashing embedder and says so.
FROM python:3.12-slim

ARG WITH_ML=1
ARG EMBEDDING_MODEL=intfloat/multilingual-e5-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/srv/services \
    HF_HOME=/opt/hf \
    HF_HUB_OFFLINE=0 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=2

WORKDIR /srv

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ffmpeg libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

COPY services/core/requirements.txt services/core/requirements-dev.txt services/core/requirements-ml.txt /tmp/
RUN pip install --upgrade pip && pip install -r /tmp/requirements-dev.txt

# Optional ML layer: CPU-only torch (the CPU wheel index keeps it small) plus
# sentence-transformers, then warm the model into /opt/hf so it ships in the
# image and the running container never needs to reach huggingface.co.
RUN if [ "$WITH_ML" = "1" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 && \
      pip install -r /tmp/requirements-ml.txt && \
      python -c "from sentence_transformers import SentenceTransformer as S; m=S('${EMBEDDING_MODEL}', device='cpu'); print('warmed ${EMBEDDING_MODEL} dim', m.get_sentence_embedding_dimension())"; \
    else \
      echo "WITH_ML=0 -> skipping torch/sentence-transformers; hashing embedder will be used"; \
    fi

COPY services /srv/services
COPY data /srv/data
COPY seeds /srv/seeds
COPY scripts /srv/scripts
COPY pipelines /srv/pipelines
COPY pyproject.toml /srv/pyproject.toml

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=12 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8000"]

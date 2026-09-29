FROM pgvector/pgvector:0.8.0-pg16

ARG POSTGIS_VERSION=3

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-16-postgis-${POSTGIS_VERSION} \
        postgresql-16-postgis-${POSTGIS_VERSION}-scripts \
    && rm -rf /var/lib/apt/lists/*

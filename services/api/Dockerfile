FROM node:22-slim AS node-runtime

FROM python:3.12-slim

WORKDIR /srv

# Verification commands are labels pinned to a zero-dependency Node harness;
# only the Node 22 runtime is needed for native TypeScript type stripping.
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node

COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY fixtures ./fixtures

RUN pip install --no-cache-dir .

ENV DEMO_MODE=true
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

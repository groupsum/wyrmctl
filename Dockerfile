FROM python:3.13-slim

WORKDIR /app
COPY packages/wyrmctl /app/packages/wyrmctl
RUN pip install --no-cache-dir /app/packages/wyrmctl

ENTRYPOINT ["wyrmctl"]

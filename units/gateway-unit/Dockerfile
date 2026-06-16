FROM python:3.11-slim

WORKDIR /app
RUN useradd -r -u 10001 app

# External deps (no sources yet — kept stable so docker layer cache hits)
RUN pip install --no-cache-dir \
        "fastapi>=0.115,<1" \
        "uvicorn[standard]>=0.30,<1" \
        "redis>=5,<6" \
        "httpx>=0.27,<1" \
        "pyjwt[crypto]>=2.8,<3" \
        "pydantic>=2.7,<3" \
        "pydantic-settings>=2.3,<3" \
        "structlog>=24.0,<25" \
        "prometheus-client>=0.20,<1" \
        "opentelemetry-api>=1.25,<2" \
        "opentelemetry-sdk>=1.25,<2"

COPY units/shared-lib /tmp/shared-lib
COPY units/gateway-unit /tmp/gateway-unit
RUN pip install --no-cache-dir --no-deps /tmp/shared-lib /tmp/gateway-unit \
 && rm -rf /tmp/shared-lib /tmp/gateway-unit

USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8080/healthz',timeout=2); sys.exit(0 if r.status==200 else 1)"

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]

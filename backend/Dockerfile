FROM python:3.11-slim

WORKDIR /app
RUN useradd -r -u 10001 app && apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 1) External deps (pinned for the demo image).
COPY backend/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt && rm /tmp/req.txt

# 2) Each unit's source — install wheels with --no-deps so the external pins
#    from step 1 win.
COPY units/shared-lib /tmp/shared-lib
COPY units/auth-unit /tmp/auth-unit
COPY units/audit-unit /tmp/audit-unit
COPY units/credential-unit /tmp/credential-unit
COPY units/data-unit /tmp/data-unit
COPY units/notebook-unit /tmp/notebook-unit
COPY units/admin-unit/backend /tmp/admin-unit-backend
COPY units/copilot-unit /tmp/copilot-unit
COPY backend /tmp/backend

RUN pip install --no-cache-dir --no-deps \
        /tmp/shared-lib \
        /tmp/auth-unit \
        /tmp/audit-unit \
        /tmp/credential-unit \
        /tmp/data-unit \
        /tmp/notebook-unit \
        /tmp/admin-unit-backend \
        /tmp/copilot-unit \
        /tmp/backend \
 && rm -rf /tmp/shared-lib /tmp/auth-unit /tmp/audit-unit /tmp/credential-unit \
           /tmp/data-unit /tmp/notebook-unit /tmp/admin-unit-backend /tmp/copilot-unit /tmp/backend

# Pre-create the shared uploads dir with permissive mode so the named volume
# (mounted at /uploads) inherits it on first creation. Backend runs as a
# non-root user and would otherwise fail with EACCES on file ingest.
RUN mkdir -p /uploads && chmod 0777 /uploads

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/healthz',timeout=2); sys.exit(0 if r.status==200 else 1)"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

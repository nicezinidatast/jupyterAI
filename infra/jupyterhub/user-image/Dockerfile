FROM jupyter/datascience-notebook:python-3.11

ARG INTERNAL_PYPI=https://pypi.org/simple/
USER root
RUN pip install --no-cache-dir --index-url $INTERNAL_PYPI \
        pandas pyarrow plotly \
        psycopg pymysql

# Install platform shared lib + Jupyter extensions when available.
# COPY units/shared-lib/dist/*.whl /tmp/
# RUN pip install --index-url $INTERNAL_PYPI /tmp/*.whl

USER ${NB_UID}

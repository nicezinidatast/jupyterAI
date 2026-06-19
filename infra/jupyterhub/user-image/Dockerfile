# 파이썬 전용 베이스. datascience-notebook(파이썬+R+Julia)을 쓰면 JupyterLab
# 런처에 R·Julia 커널 카드가 함께 떠 분석가를 혼란스럽게 한다 — 이 워크스페이스는
# 파이썬/판다스 전용이므로 scipy-notebook(파이썬 단일 커널)으로 고정한다.
FROM quay.io/jupyter/scipy-notebook:2024-10-07

ARG INTERNAL_PYPI=https://pypi.org/simple/
USER root
RUN pip install --no-cache-dir --index-url $INTERNAL_PYPI \
        pandas pyarrow plotly \
        psycopg pymysql

# Install platform shared lib + Jupyter extensions when available.
# COPY units/shared-lib/dist/*.whl /tmp/
# RUN pip install --index-url $INTERNAL_PYPI /tmp/*.whl

USER ${NB_UID}

# 파이썬 전용 베이스. datascience-notebook(파이썬+R+Julia)을 쓰면 JupyterLab
# 런처에 R·Julia 커널 카드가 함께 떠 분석가를 혼란스럽게 한다 — 이 워크스페이스는
# 파이썬/판다스 전용이므로 scipy-notebook(파이썬 단일 커널)으로 고정한다.
FROM quay.io/jupyter/scipy-notebook:2024-10-07

ARG INTERNAL_PYPI=https://pypi.org/simple/
USER root
RUN pip install --no-cache-dir --index-url $INTERNAL_PYPI \
        pandas pyarrow plotly \
        psycopg pymysql

# 커널이 메모리 부족(OOM)으로 죽으면 JupyterLab 이 "Kernel Restarting ... appears to have
# died" 다이얼로그를 띄운다. 메모리 캡(mem_limit)이 걸린 이 워크스페이스에선 갑작스런 커널
# 사망의 대부분이 OOM 이므로, 그 다이얼로그에 "관리자에게 메모리 증설 요청" 안내를 덧붙인다.
# 빌드 시 JupyterLab index.html 의 </head> 앞에 인라인 <script>(MutationObserver)를 1회 주입
# 한다 — Node 빌드/확장 패키징 없이 순수 정적 주입이라 가볍고, 인라인이라 base_url 의존도 없다.
COPY kernel-oom-notice.js inject_oom_notice.py /tmp/oom/
RUN python /tmp/oom/inject_oom_notice.py && rm -rf /tmp/oom

# Install platform shared lib + Jupyter extensions when available.
# COPY units/shared-lib/dist/*.whl /tmp/
# RUN pip install --index-url $INTERNAL_PYPI /tmp/*.whl

USER ${NB_UID}

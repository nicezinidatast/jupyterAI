# Custom JupyterLab image for the analyst workspace.
# Base scipy-notebook brings pandas / numpy / matplotlib / scikit-learn / scipy.
# We add the extras the copilot's generated code expects:
#   - jupysql + sqlalchemy + drivers → %%sql cell magic against demo DBs
#   - plotly                          → px.bar / px.line in generated snippets
#   - pyarrow / openpyxl              → parquet / xlsx read from ~/work/uploads
#
# Connection registration (so `%%sql` resolves without boilerplate) lives in
# the IPython startup script copied below.
FROM quay.io/jupyter/scipy-notebook:2024-10-07

USER root

# psycopg2-binary already ships the Postgres client lib; pymysql is pure-python.
# No system packages required.

COPY requirements.txt /tmp/jupyter-extras.txt
RUN pip install --no-cache-dir -r /tmp/jupyter-extras.txt \
 && rm /tmp/jupyter-extras.txt

# IPython startup directory — every file here runs once per kernel boot, in
# lexical order. 00- prefix runs first so later user code can rely on
# `sales_engine` / `crm_engine` / the configured `%sql` connection.
RUN mkdir -p /home/jovyan/.ipython/profile_default/startup
COPY startup/00-platform.py /home/jovyan/.ipython/profile_default/startup/00-platform.py
RUN chown -R jovyan:users /home/jovyan/.ipython

USER jovyan

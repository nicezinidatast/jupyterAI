FROM jupyterhub/jupyterhub:4.0

ARG INTERNAL_PYPI=https://pypi.org/simple/
RUN pip install --no-cache-dir --index-url $INTERNAL_PYPI \
        dockerspawner==13.0.0 \
        jupyterhub-idle-culler==1.4.0 \
        httpx>=0.27

COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
COPY platform_authenticator.py /srv/jupyterhub/platform_authenticator.py
# 사용자 볼륨 1일 정리 루프(별도 compose 서비스가 이 이미지로 실행).
COPY volume_gc.py /srv/jupyterhub/volume_gc.py
ENV PYTHONPATH=/srv/jupyterhub

EXPOSE 8000
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]

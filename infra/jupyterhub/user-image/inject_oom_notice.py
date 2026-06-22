"""빌드 시점에 커널 OOM 안내 <script> 를 JupyterLab index.html 에 1회 주입한다.

JupyterLab(LabHandler)이 렌더링하는 index.html(기본은 jupyterlab_server 패키지의
templates/index.html, 일부 빌드는 app_dir/static/index.html 이 이를 가림)의 </head> 직전에
kernel-oom-notice.js 내용을 **인라인** <script> 로 삽입한다.

인라인으로 박는 이유:
  - 외부 파일(/custom/..)로 로드하면 단일서버/허브 사용자서버의 base_url 접두에 따라 경로가
    어긋날 수 있다. 인라인은 그런 의존성이 전혀 없다.
설치된 패키지 파일에 직접 주입하는 이유:
  - LabServerApp.template_paths 설정 파일이 singleuser 서버에서 로드되는지에 의존하지 않고,
    "실제 렌더되는 템플릿"을 직접 고쳐 확실하게 적용한다. 이미지가 버전 고정이라 안전하다.

멱등: 마커가 이미 있으면 건너뛴다. 후보 템플릿이 하나도 안 잡히면 빌드를 실패시킨다(조용한
누락 방지).
"""

from __future__ import annotations

import os
import sys

# 로그 메시지에 한글/em대시가 있으므로 콘솔 로케일(예: Windows cp949, 컨테이너 LC_ALL=C)에
# 무관하게 출력이 깨지거나 UnicodeEncodeError 로 빌드가 죽지 않도록 stdout/stderr 를 UTF-8 로
# 고정한다. (reconfigure 는 Python 3.7+; 실패해도 무시.)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

MARKER = "<!-- kernel-oom-notice -->"

_here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_here, "kernel-oom-notice.js"), "r", encoding="utf-8") as fh:
    _js = fh.read()

SNIPPET = '%s\n<script type="text/javascript">\n%s\n</script>\n' % (MARKER, _js)


def _candidate_templates():
    """JupyterLab 이 렌더링할 수 있는 index.html 후보 경로들."""
    paths = []
    # 1) jupyterlab_server 패키지 템플릿 — LabHandler 의 기본 렌더 대상.
    try:
        import jupyterlab_server

        paths.append(
            os.path.join(os.path.dirname(jupyterlab_server.__file__), "templates", "index.html")
        )
    except Exception as exc:  # noqa: BLE001
        print("[oom-notice] jupyterlab_server import 실패:", exc)
    # 2) app_dir/static/index.html — 존재하면 위 템플릿을 가리므로 같이 처리.
    try:
        from jupyterlab import commands

        paths.append(os.path.join(commands.get_app_dir(), "static", "index.html"))
    except Exception as exc:  # noqa: BLE001
        print("[oom-notice] app_dir 조회 생략:", exc)
    return paths


def _inject(path: str) -> bool:
    if not os.path.isfile(path):
        print("[oom-notice] 건너뜀(없음):", path)
        return False
    with open(path, "r", encoding="utf-8") as fh:
        html = fh.read()
    if MARKER in html:
        print("[oom-notice] 이미 주입됨:", path)
        return True
    if "</head>" in html:
        html = html.replace("</head>", SNIPPET + "</head>", 1)
    elif "<body>" in html:
        html = html.replace("<body>", "<body>\n" + SNIPPET, 1)
    else:
        print("[oom-notice] <head>/<body> 앵커 없음, 건너뜀:", path)
        return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("[oom-notice] 주입 완료:", path)
    return True


def main() -> None:
    injected = sum(1 for p in _candidate_templates() if _inject(p))
    if injected == 0:
        raise SystemExit("[oom-notice] ERROR: 주입할 index.html 템플릿을 찾지 못했습니다")
    print("[oom-notice] 완료 — %d개 파일에 주입" % injected)


if __name__ == "__main__":
    main()

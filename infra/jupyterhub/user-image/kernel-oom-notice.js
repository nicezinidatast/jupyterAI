// 커널 OOM(메모리 부족) 안내 오버레이.
//
// 컨테이너에 메모리 상한(DockerSpawner.mem_limit)이 걸린 이 워크스페이스에서, 사용자가
// 큰 데이터를 다루다 한도를 넘기면 OS의 OOM 킬러가 커널 프로세스를 죽인다. 그러면
// JupyterLab 은 "Kernel Restarting / The kernel ... appears to have died. It will restart
// automatically." 다이얼로그를 띄우는데, 기본 문구만으로는 사용자가 "왜 죽었는지"를 모른다.
//
// 메모리 캡이 걸린 환경에서 갑작스런 커널 사망의 압도적 원인이 OOM 이므로, 그 다이얼로그에
// "메모리 부족일 수 있음 + 관리자에게 증설 요청" 안내를 덧붙여 사용자가 다음 행동을 알게 한다.
//
// 이 파일은 빌드 시 inject_oom_notice.py 가 JupyterLab index.html 의 </head> 앞에 인라인
// <script> 로 삽입한다(외부 로드가 아니라 인라인이라 base_url/경로 의존성이 없다).
(function () {
  "use strict";

  var NOTICE =
    "⚠ 메모리 부족(OOM)으로 커널이 종료되었을 수 있습니다. " +
    "큰 데이터를 다루는 중이었다면 표본을 줄여 다시 시도하시고, " +
    "반복되면 관리자에게 메모리 증설을 요청하십시오.";

  // 다이얼로그가 "커널 사망/재시작" 안내인지 판별한다.
  // 영어 로케일(기본)의 헤더 "Kernel Restarting" / 본문 "appears to have died" 를 우선
  // 매칭하고, 혹시 한국어 로케일이면 "커널"/"종료" 도 함께 본다.
  function kernelDeathBody(dialog) {
    var header = dialog.querySelector(".jp-Dialog-header");
    var body = dialog.querySelector(".jp-Dialog-body");
    if (!body) return null;
    var h = header ? header.textContent || "" : "";
    var b = body.textContent || "";
    if (
      h.indexOf("Kernel Restarting") !== -1 ||
      h.indexOf("커널") !== -1 ||
      b.indexOf("appears to have died") !== -1 ||
      b.indexOf("restart automatically") !== -1
    ) {
      return body;
    }
    return null;
  }

  function annotate(dialog) {
    if (!dialog || dialog.getAttribute("data-oom-notice") === "1") return;
    var body = kernelDeathBody(dialog);
    if (!body) return;
    dialog.setAttribute("data-oom-notice", "1");
    var p = document.createElement("p");
    p.className = "jp-oom-notice";
    p.textContent = NOTICE;
    p.style.cssText =
      "margin-top:10px;padding:9px 11px;border-radius:6px;" +
      "background:#fff1f2;border:1px solid #fecdd3;color:#be123c;" +
      "font-weight:600;line-height:1.55;font-size:13px";
    body.appendChild(p);
  }

  // 다이얼로그 내용이 attach 직후에 채워지는 드문 경우를 대비해 즉시 + 다음 틱 한 번 더 확인.
  function consider(dialog) {
    annotate(dialog);
    setTimeout(function () {
      annotate(dialog);
    }, 0);
  }

  function scan(node) {
    if (!node || node.nodeType !== 1) return;
    if (node.matches && node.matches("dialog.jp-Dialog")) {
      consider(node);
      return;
    }
    if (node.querySelectorAll) {
      var found = node.querySelectorAll("dialog.jp-Dialog");
      for (var i = 0; i < found.length; i++) consider(found[i]);
    }
  }

  function start() {
    // 스크립트 로드 전에 이미 떠 있던 다이얼로그도 처리.
    scan(document.body);
    // JupyterLab 다이얼로그는 document.body 의 직계 자식으로 붙으므로 subtree 없이 가볍게 감시.
    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var added = mutations[i].addedNodes;
        for (var j = 0; j < added.length; j++) scan(added[j]);
      }
    });
    observer.observe(document.body, { childList: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

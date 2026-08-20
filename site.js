/* サイト共通の処理
   - 記事ページの決裁欄を、台帳 ledger/rinji.json から描く
     （承認が台帳に記録されて初めて「承認済」の表示が出る。
       AIが承認済みの見た目を作ることはできない）
   - 記事の種別に応じた色づけ
   - トップページの件数
*/
(function () {
  var base = ((document.currentScript && document.currentScript.src) || "")
    .replace(/site\.js.*$/, "");

  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  /* 種別の色。古い記事ページにも効くよう、ラベルの文字から判定する */
  function paint() {
    var els = document.querySelectorAll(".pillar");
    for (var i = 0; i < els.length; i++) {
      var t = (els[i].textContent || "").trim();
      var cls = t === "構築記録" ? "p-build" : (t === "収集と考察" ? "p-news" : "");
      if (!cls) continue;
      var host = els[i].closest(".entry") || els[i].closest(".dig") || document.body;
      host.classList.add(cls);
    }
  }

  /* ── 決裁欄 ── */
  var SEAL_OK =
    '<svg class="stamp" viewBox="0 0 100 100" role="img" aria-label="承認済">' +
    '<circle cx="50" cy="50" r="46" fill="none" stroke="#C0392F" stroke-width="3.5"/>' +
    '<line x1="10" y1="50" x2="90" y2="50" stroke="#C0392F" stroke-width="1.6"/>' +
    '<text x="50" y="34" font-family="serif" font-size="27" fill="#C0392F" text-anchor="middle">承認</text>' +
    '<text x="50" y="73" font-family="serif" font-size="19" fill="#C0392F" text-anchor="middle">済</text>' +
    "</svg>";

  var SEAL_WAIT =
    '<svg class="stamp" viewBox="0 0 100 100" role="img" aria-label="承認待ち">' +
    '<circle cx="50" cy="50" r="46" fill="none" stroke="#CFCBC1" stroke-width="2.5" stroke-dasharray="5 5"/>' +
    '<text x="50" y="57" font-family="serif" font-size="17" fill="#A8A399" text-anchor="middle">未承認</text>' +
    "</svg>";

  function stampbox(box, r) {
    var no = box.getAttribute("data-rinji") || "";
    var ok = r && r.status === "approved";
    var line = ok
      ? "承認　<em>" + esc(r.approved_by) + "</em>　" + esc(r.approved_at)
      : '承認　<span class="pend">まだ承認されていません</span>';
    box.innerHTML =
      (ok ? SEAL_OK : SEAL_WAIT) +
      '<div class="stampinfo">' +
      "稟議番号　<em>" + esc(no) + "</em><br>" +
      "起案　<em>SKY SOCIAL LAB / Claude</em><br>" +
      line +
      "</div>";
  }

  /* ── 台帳を読む ── */
  function ledger() {
    var box = document.querySelector(".stampbox[data-rinji]");
    var stats = document.querySelector(".stats");
    if (!box && !stats) return;

    fetch(base + "ledger/rinji.json").then(function (r) {
      return r.json();
    }).then(function (d) {
      var rows = d.rinji || [];
      if (box) {
        var no = box.getAttribute("data-rinji");
        var hit = null;
        for (var i = 0; i < rows.length; i++) if (rows[i].no === no) hit = rows[i];
        stampbox(box, hit);
      }
      if (stats) {
        var n = { approved: 0, pending: 0 };
        for (var j = 0; j < rows.length; j++) {
          if (n[rows[j].status] !== undefined) n[rows[j].status]++;
        }
        var set = function (id, v) {
          var el = document.getElementById(id);
          if (el) el.textContent = v;
        };
        set("s-ok", n.approved);
        set("s-wait", n.pending);
      }
    }).catch(function () {
      if (box) stampbox(box, null);
    });
  }

  function init() { paint(); ledger(); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else { init(); }
})();

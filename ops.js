/* 稼働状況ページの処理
   GitHub Actionsの実行履歴を、GitHub APIから直接読んで表示する。
   キャラクターのアニメーションは演出だが、状態（動いている／止まっている／
   成功／失敗）そのものは常に実データに基づく。数字も状態も作らない。 */
(function () {
  var REPO = "SKYSOCIAL-Shohei/sky-lab";
  var API = "https://api.github.com/repos/" + REPO;
  var POLL_MS = 90000;

  var AGENTS = [
    { workflow: "毎朝の起案", name: "起案エージェント",
      role: "毎朝、公開情報の収集・記事の起案・記事ページの作成・検査・PR作成までを行う" },
    { workflow: "承認の記録", name: "承認記録エージェント",
      role: "人間がGitHub上で行ったレビュー承認を検知し、台帳へ記録する" },
    { workflow: "PRをbot名義で作成", name: "PR作成エージェント",
      role: "人間の個人アカウントで作ったブランチを、bot名義のPRに仕立てる" },
    { workflow: "事後承認PRを作成", name: "事後承認エージェント",
      role: "「収集と考察」に限り、公開後の事後承認PRを作る" },
    { workflow: "下書きから記事を作成（手動投入）", name: "手動投入エージェント",
      role: "API経由で生成できない下書きを、確認済みのテキストとして記事化する" },
    { workflow: "公開前セキュリティ検査", name: "検査エージェント",
      role: "pushとPRのたびに、情報漏れ・未承認公開がないかを調べる" }
  ];

  var lastStatusKey = {}; // workflow名 -> 直前の状態文字列。変化検知のためだけに使う

  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  function fmtTime(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" +
      String(d.getDate()).padStart(2, "0") + " " +
      String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }

  function relTime(iso) {
    if (!iso) return "";
    var ms = Date.now() - new Date(iso).getTime();
    var min = Math.floor(ms / 60000);
    if (min < 1) return "たった今";
    if (min < 60) return min + "分前";
    var hr = Math.floor(min / 60);
    if (hr < 24) return hr + "時間前";
    return Math.floor(hr / 24) + "日前";
  }

  /* 机＋モニター＋キャラクターのSVG。状態はCSSクラス（desk.状態）だけで切り替える */
  function charSvg() {
    return '<svg class="char" viewBox="0 0 120 92" aria-hidden="true">'
      + '<rect x="10" y="70" width="100" height="7" rx="2" class="desktop"/>'
      + '<rect x="18" y="77" width="6" height="13" class="leg"/>'
      + '<rect x="96" y="77" width="6" height="13" class="leg"/>'
      + '<rect x="35" y="28" width="50" height="34" rx="3" class="monitor"/>'
      + '<rect x="39" y="32" width="42" height="26" rx="1" class="screen"/>'
      + '<rect x="42" y="37" width="20" height="2.6" class="line l1"/>'
      + '<rect x="42" y="42" width="30" height="2.6" class="line l2"/>'
      + '<rect x="42" y="47" width="14" height="2.6" class="line l3"/>'
      + '<rect x="42" y="52" width="24" height="2.6" class="line l4"/>'
      + '<rect x="56" y="62" width="8" height="6" class="stand"/>'
      + '<circle cx="60" cy="15" r="9" class="head"/>'
      + '<rect x="49" y="24" width="22" height="16" rx="6" class="body"/>'
      + '<circle cx="60" cy="46" r="44" class="ring"/>'
      + '</svg>';
  }

  function stateOf(run) {
    if (!run) return "never";
    if (run.status !== "completed") return "working";
    if (run.conclusion === "success") return "success";
    if (run.conclusion === "failure") return "fail";
    return "idle";
  }

  function pillHtml(state, run) {
    if (state === "never") return '<span class="pill wait">未実行</span>';
    if (state === "working") return '<span class="pill wait">実行中</span>';
    if (state === "success") return '<span class="pill ok">成功</span>';
    if (state === "fail") return '<span class="pill bad">失敗</span>';
    return '<span class="pill">' + esc(run.conclusion || run.status) + '</span>';
  }

  function renderAgents(runsByName, failed) {
    var box = document.getElementById("agents");
    if (failed) {
      box.innerHTML = '<p class="empty">GitHub APIから読めませんでした（レート制限の可能性があります）。'
        + '<br><a href="https://github.com/' + esc(REPO) + '/actions">GitHub上のActions一覧を直接見る</a></p>';
      return;
    }
    var html = AGENTS.map(function (a) {
      var run = runsByName[a.workflow];
      var state = stateOf(run);
      var key = run ? run.status + ":" + (run.conclusion || "") : "never";
      var justChanged = lastStatusKey[a.workflow] !== undefined && lastStatusKey[a.workflow] !== key;
      lastStatusKey[a.workflow] = key;

      return '<div class="desk ' + state + (justChanged ? ' just' : '') + '" data-wf="' + esc(a.workflow) + '">'
        + charSvg()
        + '<div class="desk-name">' + esc(a.name) + '</div>'
        + '<div class="desk-role">' + esc(a.role) + '</div>'
        + '<div class="desk-foot">'
        + pillHtml(state, run)
        + (run ? '<a class="desk-log" href="' + esc(run.html_url) + '">ログ</a>' : '')
        + '</div>'
        + (run ? '<div class="desk-when">' + esc(relTime(run.created_at)) + '（' + esc(fmtTime(run.created_at)) + '）</div>' : '')
        + '</div>';
    }).join("");
    box.innerHTML = html;

    // 変化した机だけ、一度だけの演出クラスを少し後で外す
    var justEls = box.querySelectorAll(".desk.just");
    for (var i = 0; i < justEls.length; i++) {
      (function (el) { setTimeout(function () { el.classList.remove("just"); }, 700); })(justEls[i]);
    }
  }

  function renderNippou(d) {
    var box = document.getElementById("nippou");
    var days = (d && d.days) || [];
    if (!days.length) { box.innerHTML = '<p class="empty">記録がありません。</p>'; return; }
    var day = days[0];
    var entries = day.entries || [];
    if (!entries.length) {
      box.innerHTML = '<p class="empty">' + esc(day.date) + ' の記録はまだありません。</p>';
      return;
    }
    box.innerHTML = entries.map(function (e) {
      return '<div class="log-row">'
        + '<span class="log-who">' + esc(e.who || "") + '</span>'
        + '<span class="log-what">' + esc(e.what || "") + '</span>'
        + '<span class="log-when">' + esc(day.date) + '</span>'
        + '</div>';
    }).join("");
  }

  var busy = false;
  function poll() {
    if (busy) return;
    busy = true;
    fetch(API + "/actions/runs?per_page=60")
      .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
      .then(function (d) {
        var runs = d.workflow_runs || [];
        var latest = {}, newest = null;
        for (var i = 0; i < runs.length; i++) {
          var name = runs[i].name;
          if (!latest[name] || new Date(runs[i].created_at) > new Date(latest[name].created_at)) {
            latest[name] = runs[i];
          }
          if (!newest || new Date(runs[i].created_at) > new Date(newest)) newest = runs[i].created_at;
        }
        renderAgents(latest, false);
        setPulse(newest);
      })
      .catch(function () { renderAgents({}, true); })
      .finally(function () { busy = false; });
  }

  function setPulse(newestIso) {
    var dot = document.getElementById("pulse");
    var label = document.getElementById("pulse-label");
    if (!newestIso) { dot.classList.remove("on"); label.textContent = "確認できず"; return; }
    var hrs = (Date.now() - new Date(newestIso).getTime()) / 3600000;
    if (hrs < 26) {
      dot.classList.add("on");
      label.textContent = "稼働中（直近の実行 " + relTime(newestIso) + "）";
    } else {
      dot.classList.remove("on");
      label.textContent = "しばらく実行がありません（" + relTime(newestIso) + "）";
    }
  }

  function tickClock() {
    var el = document.getElementById("clock");
    if (!el) return;
    var d = new Date();
    el.textContent = String(d.getHours()).padStart(2, "0") + ":" +
      String(d.getMinutes()).padStart(2, "0") + ":" + String(d.getSeconds()).padStart(2, "0");
  }

  document.getElementById("refresh-btn").addEventListener("click", poll);
  setInterval(poll, POLL_MS);
  setInterval(tickClock, 1000);
  tickClock();
  poll();

  fetch("ledger/nippou.json").then(function (r) { return r.json(); }).then(renderNippou)
    .catch(function () { document.getElementById("nippou").innerHTML = '<p class="empty">読み込めませんでした。</p>'; });
})();

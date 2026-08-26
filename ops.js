/* 稼働状況ページの処理
   GitHub Actionsの実行履歴を、GitHub APIから直接読んで表示する。
   集計・演出はしない。読めなかった場合は「読めなかった」と表示する。 */
(function () {
  var REPO = "SKYSOCIAL-Shohei/sky-lab";
  var API = "https://api.github.com/repos/" + REPO;

  var AGENTS = [
    { workflow: "毎朝の起案", name: "起案エージェント",
      role: "毎朝、公開情報の収集・記事の起案・記事ページの作成・検査・PR作成までを行う" },
    { workflow: "承認の記録", name: "承認記録エージェント",
      role: "人間がGitHub上で行ったレビュー承認を検知し、台帳へ記録する" },
    { workflow: "PRをbot名義で作成", name: "PR作成エージェント",
      role: "人間の個人アカウントで作ったブランチを、bot名義のPRに仕立てる（自分のPRを自分で承認できないGitHubの制限を避けるため）" },
    { workflow: "事後承認PRを作成", name: "事後承認エージェント",
      role: "「収集と考察」に限り、公開後の事後承認PRを作る" },
    { workflow: "下書きから記事を作成（手動投入）", name: "手動投入エージェント",
      role: "API経由で生成できない下書き（社外秘資料を材料にしたものなど）を、確認済みのテキストとして記事化する" },
    { workflow: "公開前セキュリティ検査", name: "検査エージェント",
      role: "pushとPRのたびに、情報漏れ・未承認公開がないかを調べる" }
  ];

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

  function badge(run) {
    if (!run) return '<span class="badge wait">記録なし</span>';
    if (run.status !== "completed") return '<span class="badge wait">実行中</span>';
    if (run.conclusion === "success") return '<span class="badge ok">成功</span>';
    if (run.conclusion === "failure") return '<span class="badge ng">失敗</span>';
    return '<span class="badge wait">' + esc(run.conclusion || run.status) + '</span>';
  }

  function renderAgents(runsByName, failed) {
    var box = document.getElementById("agents");
    if (failed) {
      box.innerHTML = '<p class="empty">GitHub APIから読めませんでした（レート制限の可能性があります）。時間をおいて再読み込みしてください。'
        + '<br><a href="https://github.com/' + esc(REPO) + '/actions">GitHub上のActions一覧を直接見る</a></p>';
      return;
    }
    var rows = AGENTS.map(function (a) {
      var run = runsByName[a.workflow];
      return '<div class="opsrow">'
        + '<div class="opsrow-hd"><span class="opsname">' + esc(a.name) + '</span>' + badge(run) + '</div>'
        + '<div class="opsrole">' + esc(a.role) + '</div>'
        + (run
            ? '<div class="opsmeta">直近の実行　' + esc(fmtTime(run.created_at))
              + '　<a href="' + esc(run.html_url) + '">実行ログを見る</a></div>'
            : '<div class="opsmeta">まだ一度も実行されていません</div>')
        + '</div>';
    });
    box.innerHTML = rows.join("");
  }

  function renderNippou(d) {
    var box = document.getElementById("nippou");
    var days = (d && d.days) || [];
    if (!days.length) {
      box.innerHTML = '<p class="empty">記録がありません。</p>';
      return;
    }
    var day = days[0];
    var entries = day.entries || [];
    if (!entries.length) {
      box.innerHTML = '<p class="empty">' + esc(day.date) + ' の記録はまだありません。</p>';
      return;
    }
    var rows = entries.map(function (e) {
      return '<div class="opsrow"><div class="opsrow-hd"><span class="opsname">' + esc(e.who || "") + '</span>'
        + '<span class="opsmeta">' + esc(day.date) + (e.time && e.time !== "—" ? " " + esc(e.time) : "") + '</span></div>'
        + '<div class="opsrole">' + esc(e.what || "") + '</div></div>';
    });
    box.innerHTML = rows.join("");
  }

  fetch(API + "/actions/runs?per_page=60")
    .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
    .then(function (d) {
      var runs = d.workflow_runs || [];
      var latest = {};
      for (var i = 0; i < runs.length; i++) {
        var name = runs[i].name;
        if (!latest[name] || new Date(runs[i].created_at) > new Date(latest[name].created_at)) {
          latest[name] = runs[i];
        }
      }
      renderAgents(latest, false);
    })
    .catch(function () { renderAgents({}, true); });

  fetch("ledger/nippou.json")
    .then(function (r) { return r.json(); })
    .then(renderNippou)
    .catch(function () {
      document.getElementById("nippou").innerHTML = '<p class="empty">読み込めませんでした。</p>';
    });
})();

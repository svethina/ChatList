(() => {
  const REPO = "svethina/ChatList";
  const meta = document.getElementById("release-meta");
  const btn = document.getElementById("download-btn");
  if (!meta || !btn) return;

  const fallback = `https://github.com/${REPO}/releases/latest`;

  fetch(`https://api.github.com/repos/${REPO}/releases/latest`)
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((data) => {
      const tag = data.tag_name || "";
      const assets = Array.isArray(data.assets) ? data.assets : [];
      const installer = assets.find((a) =>
        /^ChatList-Setup-.*\.exe$/i.test(a.name)
      );
      const portable = assets.find((a) =>
        /^ChatList\.exe$/i.test(a.name)
      );
      const asset = installer || portable;

      if (asset && asset.browser_download_url) {
        btn.href = asset.browser_download_url;
        btn.textContent = installer
          ? "Скачать установщик"
          : "Скачать ChatList.exe";
      } else {
        btn.href = fallback;
      }

      const when = data.published_at
        ? new Date(data.published_at).toLocaleDateString("ru-RU")
        : "";
      meta.textContent = tag
        ? `Последний релиз ${tag}${when ? ` · ${when}` : ""}`
        : "Релизы появятся после первой публикации.";
    })
    .catch(() => {
      btn.href = fallback;
      meta.textContent =
        "Откройте страницу релизов на GitHub, чтобы скачать установщик.";
    });
})();

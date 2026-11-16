// In-page artifact viewer: flip through pages inline, or open full screen.
(function () {
  var dlg;

  function buildDialog() {
    dlg = document.createElement("dialog");
    dlg.className = "lightbox";
    dlg.innerHTML =
      '<div class="lb-head"><span class="lb-title"></span><span class="lb-count"></span>' +
      '<button class="lb-close" type="button" aria-label="Close">✕</button></div>' +
      '<div class="lb-stage"><button class="lb-prev" type="button" aria-label="Previous page">‹</button>' +
      '<img alt=""><button class="lb-next" type="button" aria-label="Next page">›</button></div>';
    document.body.appendChild(dlg);
    dlg.querySelector(".lb-close").onclick = function () { dlg.close(); };
    dlg.addEventListener("click", function (e) { if (e.target === dlg) dlg.close(); });
    dlg.querySelector(".lb-prev").onclick = function () { dlg._go(-1); };
    dlg.querySelector(".lb-next").onclick = function () { dlg._go(1); };
    dlg.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") dlg._go(-1);
      if (e.key === "ArrowRight") dlg._go(1);
    });
    swipe(dlg.querySelector(".lb-stage"), function (d) { dlg._go(d); });
    dlg.addEventListener("close", function () { document.body.classList.remove("lb-open"); });
  }

  function swipe(el, fn) {
    var x0 = null;
    el.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    el.addEventListener("touchend", function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 40) fn(dx < 0 ? 1 : -1);
      x0 = null;
    });
  }

  function openFull(pages, start, title, onChange) {
    if (!dlg) buildDialog();
    var i = start;
    var img = dlg.querySelector("img");
    dlg.querySelector(".lb-title").textContent = title;
    var multi = pages.length > 1;
    dlg.querySelector(".lb-prev").hidden = !multi;
    dlg.querySelector(".lb-next").hidden = !multi;
    dlg._go = function (d) {
      i = Math.max(0, Math.min(pages.length - 1, i + d));
      img.src = pages[i];
      img.alt = title + ", page " + (i + 1);
      dlg.querySelector(".lb-count").textContent = multi ? (i + 1) + " / " + pages.length : "";
      onChange(i);
    };
    dlg._go(0);
    document.body.classList.add("lb-open");
    dlg.showModal();
  }

  document.querySelectorAll(".viewer[data-pages]").forEach(function (v) {
    var pages = JSON.parse(v.getAttribute("data-pages"));
    var title = v.getAttribute("data-title");
    var img = v.querySelector(".v-stage img");
    var count = v.querySelector(".v-count");
    var i = 0;
    function show(n) {
      i = Math.max(0, Math.min(pages.length - 1, n));
      img.src = pages[i];
      if (count) count.textContent = (i + 1) + " / " + pages.length;
      var p = v.querySelector(".v-prev"), nx = v.querySelector(".v-next");
      if (p) p.disabled = i === 0;
      if (nx) nx.disabled = i === pages.length - 1;
      if (pages[i + 1]) new Image().src = pages[i + 1];
    }
    var prev = v.querySelector(".v-prev"), next = v.querySelector(".v-next");
    if (prev) prev.onclick = function () { show(i - 1); };
    if (next) next.onclick = function () { show(i + 1); };
    swipe(v.querySelector(".v-stage"), function (d) { show(i + d); });
    function full() { openFull(pages, i, title, show); }
    v.querySelector(".v-stage").onclick = full;
    v.querySelector(".v-full").onclick = full;
    show(0);
  });
})();

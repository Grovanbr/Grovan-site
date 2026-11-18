/* Funções comuns das calculadoras da Grovan */
window.Calc = (function () {
  const WHATS = "5511945426510";
  function num(v) {
    if (v == null) return 0;
    let s = String(v).replace(/[R$\s%]/g, "");
    if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
    const n = parseFloat(s);
    return isFinite(n) ? n : 0;
  }
  function val(id) { const el = document.getElementById(id); return el ? num(el.value) : 0; }
  function brl(n) { return (isFinite(n) ? n : 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
  function pct(n, casas) { return (isFinite(n) ? n : 0).toLocaleString("pt-BR", { maximumFractionDigits: casas == null ? 1 : casas }) + "%"; }
  function set(id, txt) { const el = document.getElementById(id); if (el) el.textContent = txt; }
  function linhas(id, itens) {
    const ul = document.getElementById(id); if (!ul) return;
    ul.innerHTML = "";
    itens.forEach(([rotulo, valor, total]) => {
      const li = document.createElement("li");
      if (total) li.className = "total";
      const a = document.createElement("span"); a.textContent = rotulo;
      const b = document.createElement("b"); b.textContent = valor;
      li.append(a, b); ul.append(li);
    });
  }
  function aviso(id, texto, tipo) {
    const el = document.getElementById(id); if (!el) return;
    el.hidden = !texto; el.textContent = texto || ""; el.className = "calc-aviso" + (tipo ? " " + tipo : "");
  }
  function whats(id, texto) {
    const el = document.getElementById(id); if (el) el.href = "https://wa.me/" + WHATS + "?text=" + encodeURIComponent(texto);
  }
  function ligar(form, fn) {
    const f = typeof form === "string" ? document.getElementById(form) : form;
    f.addEventListener("input", fn); f.addEventListener("change", fn);
    f.addEventListener("submit", e => e.preventDefault());
    fn();
  }
  return { num, val, brl, pct, set, linhas, aviso, whats, ligar };
})();

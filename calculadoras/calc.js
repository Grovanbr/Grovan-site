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
  const SB = { url: "https://gemsxocgwkpkgapgflkt.supabase.co", key: "sb_publishable_CIgMVDHTDKmTEfzttKyCqA_WktHZV13" };
  function telefone(v) { let d = String(v || "").replace(/\D/g, ""); if (d.length === 10 || d.length === 11) d = "55" + d; return /^55\d{10,11}$/.test(d) ? d : null; }
  async function salvarContato(dados) {
    try {
      const r = await fetch(SB.url + "/rest/v1/contatos_site", { method: "POST", headers: { "content-type": "application/json", apikey: SB.key, prefer: "return=minimal" }, body: JSON.stringify(dados) });
      return r.ok;
    } catch (e) { return false; }
  }
  return { num, val, brl, pct, set, linhas, aviso, whats, ligar, telefone, salvarContato, WHATS };
})();

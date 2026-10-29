/*
  Botão de tema claro/escuro.
  A escolha fica salva no navegador da pessoa. Se ela nunca escolheu,
  o site segue o tema do celular ou do computador.
*/
(function () {
  const raiz = document.documentElement;

  function aplicar(tema) {
    raiz.dataset.tema = tema;
    document.querySelectorAll(".botao-tema").forEach(botao => {
      const escuro = tema === "escuro";
      botao.setAttribute("aria-pressed", escuro ? "true" : "false");
      botao.setAttribute("aria-label", escuro ? "Mudar para o tema claro" : "Mudar para o tema escuro");
    });
  }

  aplicar(raiz.dataset.tema || "claro");

  document.querySelectorAll(".botao-tema").forEach(botao => {
    botao.addEventListener("click", () => {
      const novo = raiz.dataset.tema === "escuro" ? "claro" : "escuro";
      aplicar(novo);
      try {
        localStorage.setItem("grovan-tema", novo);
      } catch (e) {
        // Se o navegador bloquear, o tema só não fica salvo
      }
    });
  });
})();

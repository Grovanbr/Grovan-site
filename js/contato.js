/*
  Formulário da página Contato.
  Não envia nada para servidor: monta a mensagem e abre o WhatsApp
  com o texto já escrito. A pessoa só confere e aperta enviar.
*/
const NUMERO_WHATSAPP = "5511945426510";

document.getElementById("form-contato").addEventListener("submit", evento => {
  evento.preventDefault();
  const dados = new FormData(evento.target);

  const texto =
    "Olá, Grovan! Meu nome é " + dados.get("nome").trim() + ".\n" +
    "Assunto: " + dados.get("assunto") + "\n\n" +
    dados.get("mensagem").trim();

  window.open("https://wa.me/" + NUMERO_WHATSAPP + "?text=" + encodeURIComponent(texto), "_blank", "noopener");
});

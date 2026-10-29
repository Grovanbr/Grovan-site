/*
  Banner rotativo da página Achados.
  Este arquivo é gerado pelo Painel Grovan (tela Banners).

  configBanner.segundos -> quanto tempo cada banner fica na tela
  banners -> a ordem do banner. Dois tipos:
    { tipo: "produto", nome: "..." }  -> um produto marcado com estrela (destaque)
    { tipo: "imagem", titulo, imagem, imagemCelular, link, ativo } -> arte própria
  Produtos com estrela que não estiverem na lista entram no final.
*/

const configBanner = {"segundos": 5};

const banners = [];

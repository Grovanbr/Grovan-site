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

const banners = [
  {
    "tipo": "produto",
    "nome": "Nome do produto de cozinha"
  },
  {
    "tipo": "produto",
    "nome": "Secret Boom Box Gloss Labial Com Chaveiro De Ursinho Sortido"
  },
  {
    "tipo": "produto",
    "nome": "Nome do produto de tecnologia"
  },
  {
    "tipo": "produto",
    "nome": "Outro produto de tecnologia"
  },
  {
    "tipo": "produto",
    "nome": "Escovas Para Maquiagem Multicolor Kit 8 Peças Pincel Macio Sortida"
  },
  {
    "tipo": "produto",
    "nome": "Guarda Chuva Grande Reforçado Contra Vento Cabe Na Bolsa"
  }
];

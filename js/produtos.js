/*
  =====================================================================
  LISTA DE PRODUTOS DA PÁGINA ACHADOS
  =====================================================================
  Para ADICIONAR um produto: copie um bloco { ... }, inclusive a vírgula
  do final, cole na lista e troque os dados.

  Campos:
    nome         -> nome do produto (entre aspas)
    loja         -> "Shopee", "Mercado Livre", "Amazon", "Magalu"...
    categoria    -> "Casa", "Cozinha" ou "Tecnologia"
                    (pode criar outra: ela aparece sozinha nos filtros)
    link         -> seu link de afiliado
    imagem       -> link da foto do produto (opcional; deixe "" se não tiver)
    preco        -> preço atual, com ponto no lugar da vírgula (ex.: 49.90)
    precoAntigo  -> preço antes do desconto (opcional; use 0 se não tiver)
    destaque     -> true para aparecer em "Ofertas em destaque", false se não

  Para REMOVER um produto: apague o bloco { ... } inteiro.

  Dica para a imagem: na página do produto na loja, clique com o botão
  direito na foto e escolha "Copiar endereço da imagem".
  =====================================================================
*/

const produtos = [
  {
    nome: "Secret Boom Box Gloss Labial Com Chaveiro De Ursinho Sortido",
    loja: "Mercado Livre",
    categoria: "Beleza",
    link: "https://meli.la/251SmGp",
    imagem: "https://http2.mlstatic.com/D_NQ_NP_606455-MLB117287382722_102026-O.webp",
    preco: 137.34,
    precoAntigo: 144.99,
    destaque: true
  },
  {
    nome: "Nome do produto de cozinha",
    loja: "Mercado Livre",
    categoria: "Cozinha",
    link: "#",
    imagem: "",
    preco: 89.90,
    precoAntigo: 129.90,
    destaque: true
  },
  {
    nome: "Nome do produto de tecnologia",
    loja: "Amazon",
    categoria: "Tecnologia",
    link: "#",
    imagem: "",
    preco: 149.90,
    precoAntigo: 199.90,
    destaque: true
  },
  {
    nome: "Outro produto de casa",
    loja: "Mercado Livre",
    categoria: "Casa",
    link: "#",
    imagem: "",
    preco: 24.90,
    precoAntigo: 0.00,
    destaque: false
  },
  {
    nome: "Outro produto de cozinha",
    loja: "Shopee",
    categoria: "Cozinha",
    link: "#",
    imagem: "",
    preco: 19.90,
    precoAntigo: 34.90,
    destaque: false
  },
  {
    nome: "Outro produto de tecnologia",
    loja: "Shopee",
    categoria: "Tecnologia",
    link: "#",
    imagem: "",
    preco: 59.90,
    precoAntigo: 99.90,
    destaque: true
  },
  {
    nome: "Escovas Para Maquiagem Multicolor Kit 8 Peças Pincel Macio Sortida",
    loja: "Mercado Livre",
    categoria: "Beleza",
    link: "https://meli.la/1uWXStd",
    imagem: "https://http2.mlstatic.com/D_NQ_NP_683755-MLB112552959736_062026-O.webp",
    preco: 27.42,
    precoAntigo: 42.84,
    destaque: true
  },
  {
    nome: "Guarda Chuva Grande Reforçado Contra Vento Cabe Na Bolsa",
    loja: "Mercado Livre",
    categoria: "Guarda-chuva",
    link: "https://meli.la/1QaP3Rj",
    imagem: "https://http2.mlstatic.com/D_NQ_NP_970861-MLB89352137022_082025-O.webp",
    preco: 26.24,
    precoAntigo: 36.90,
    destaque: true
  },
];

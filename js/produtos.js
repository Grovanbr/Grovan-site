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
    imagem: "https://http2.mlstatic.com/D_NQ_NP_606455-MLB117287382722_102026-F.webp",
    preco: 141.99,
    precoAntigo: 197.49,
    destaque: true
  },
  {
    nome: "Escovas Para Maquiagem Multicolor Kit 8 Peças Pincel Macio Sortida",
    loja: "Mercado Livre",
    categoria: "Beleza",
    link: "https://meli.la/1uWXStd",
    imagem: "https://http2.mlstatic.com/D_NQ_NP_683755-MLB112552959736_062026-F.webp",
    preco: 26.72,
    precoAntigo: 42.84,
    destaque: true
  },
  {
    nome: "Guarda Chuva Grande Reforçado Contra Vento Cabe Na Bolsa",
    loja: "Shopee",
    categoria: "Guarda-chuva",
    link: "https://s.shopee.com.br/9AQ6EZtUvK",
    imagem: "https://cf.shopee.com.br/file/sg-11134201-22100-l9d7cwr2esiv24",
    preco: 22.90,
    precoAntigo: 0.00,
    destaque: true,
    shopee: "448628081.19455451486"
  },
  {
    nome: "Árvore de Natal 1,50cm 400 Galhos Pinheiro Verde Resistente Desmontável Pé de Ferro e Plástico",
    loja: "Shopee",
    categoria: "Artigos de Festa",
    link: "https://s.shopee.com.br/8AXZ3P2GAs",
    imagem: "https://cf.shopee.com.br/file/br-11134207-820lh-msn53tgvj952b7",
    preco: 85.90,
    precoAntigo: 0.00,
    destaque: true,
    shopee: "1475886431.57717240116"
  },
  {
    nome: "Principia Kit Limpeza E Hidratação Ch-01 + Ol-01 + Gl-02 Todo Tipo De Pele Dia/noite",
    loja: "Mercado Livre",
    categoria: "Beleza",
    link: "https://meli.la/1ikSs3S",
    imagem: "https://http2.mlstatic.com/D_NQ_NP_609209-MLA94364515810_102025-F.webp",
    preco: 95.55,
    precoAntigo: 147.00,
    destaque: true
  },
  {
    nome: "NIVEA Loção Deo-Hidratante Soft Milk 400ml, Hidratação Profunda 72h, Hialurônico Puro, Corporal, Pele Seca",
    loja: "Mercado Livre",
    categoria: "Beleza",
    link: "https://meli.la/2Mg6D1e",
    imagem: "https://http2.mlstatic.com/D_NQ_NP_756821-MLA86791313939_062025-F.webp",
    preco: 15.43,
    precoAntigo: 26.99,
    destaque: false
  },
  {
    nome: "Kit 100 Bolas de Natal com Estrela ou Kit 50 Enfeite Árvore Vermelha Dourada Mista Fosca Glitter",
    loja: "Shopee",
    categoria: "Artigos de Festa",
    link: "https://s.shopee.com.br/9V2xcO7s3w",
    imagem: "https://cf.shopee.com.br/file/sg-11134201-82584-mu0wlh0ytywz41",
    preco: 79.90,
    precoAntigo: 150.75,
    destaque: false,
    shopee: "1340072116.22394461600"
  },
];

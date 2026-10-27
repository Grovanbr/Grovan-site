/*
  Monta a página de Achados a partir da lista em produtos.js.
  Você não precisa mexer neste arquivo para adicionar produtos.
*/

// ===== Ícones das categorias (desenhos SVG) =====
const icones = {
  casa: '<path d="M3 11l9-7 9 7M5 10v10h14V10"/>',
  cozinha: '<path d="M6 3v8a3 3 0 0 0 6 0V3M9 3v18M17 3c-2 2-2 6 0 8v10"/>',
  tecnologia: '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
  padrao: '<path d="M6 7h12l-1 13H7L6 7zM9 7a3 3 0 0 1 6 0"/>'
};

// ===== Estado da página (o que está filtrado agora) =====
const filtro = {
  categoria: "Todos",
  lojas: [],
  busca: "",
  ordem: "relevancia",
  soFavoritos: false
};

// ===== Favoritos (ficam salvos no navegador da pessoa) =====
let favoritos = [];
try {
  favoritos = JSON.parse(localStorage.getItem("grovan-favoritos")) || [];
} catch (e) {
  favoritos = [];
}

function salvarFavoritos() {
  try {
    localStorage.setItem("grovan-favoritos", JSON.stringify(favoritos));
  } catch (e) {
    // Se o navegador bloquear, os favoritos só não ficam salvos
  }
}

// ===== Funções de apoio =====
function semAcento(texto) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function formatarPreco(valor) {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function desconto(produto) {
  if (!produto.precoAntigo || produto.precoAntigo <= produto.preco) return 0;
  return Math.round((1 - produto.preco / produto.precoAntigo) * 100);
}

function svgIcone(categoria) {
  const chave = semAcento(categoria);
  const desenho = icones[chave] || icones.padrao;
  return '<svg viewBox="0 0 24 24" aria-hidden="true">' + desenho + "</svg>";
}

function criar(tag, classe, texto) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

// Lista de categorias e lojas tiradas dos próprios produtos
const categorias = [...new Set(produtos.map(p => p.categoria))];
const lojas = [...new Set(produtos.map(p => p.loja))];

// ===== Card de um produto =====
function cardProduto(produto) {
  const card = criar("article", "oferta");

  // Imagem
  const imagem = criar("div", "oferta-imagem");
  if (produto.imagem) {
    const img = document.createElement("img");
    img.src = produto.imagem;
    img.alt = produto.nome;
    img.loading = "lazy";
    imagem.appendChild(img);
  } else {
    imagem.innerHTML = svgIcone(produto.categoria);
  }

  const pct = desconto(produto);
  if (pct > 0) imagem.appendChild(criar("span", "oferta-desconto", "-" + pct + "%"));
  imagem.appendChild(criar("span", "oferta-loja", produto.loja));

  // Botão de favorito
  const fav = criar("button", "oferta-favorito");
  fav.type = "button";
  const ehFavorito = favoritos.includes(produto.nome);
  fav.setAttribute("aria-pressed", ehFavorito ? "true" : "false");
  fav.setAttribute("aria-label", ehFavorito ? "Remover dos favoritos" : "Adicionar aos favoritos");
  fav.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/></svg>';
  fav.addEventListener("click", () => {
    if (favoritos.includes(produto.nome)) {
      favoritos = favoritos.filter(n => n !== produto.nome);
    } else {
      favoritos.push(produto.nome);
    }
    salvarFavoritos();
    atualizarTudo();
  });
  imagem.appendChild(fav);

  card.appendChild(imagem);

  // Informações
  const info = criar("div", "oferta-info");
  info.appendChild(criar("span", "oferta-categoria", produto.categoria));
  info.appendChild(criar("h3", "oferta-nome", produto.nome));

  const precos = criar("div", "oferta-precos");
  if (pct > 0) precos.appendChild(criar("s", "oferta-preco-antigo", formatarPreco(produto.precoAntigo)));
  precos.appendChild(criar("strong", "oferta-preco", formatarPreco(produto.preco)));
  info.appendChild(precos);

  const botao = criar("a", "oferta-botao", "Ver oferta →");
  botao.href = produto.link;
  botao.target = "_blank";
  botao.rel = "noopener sponsored";
  info.appendChild(botao);

  card.appendChild(info);
  return card;
}

// ===== Pílulas de categoria (barra de cima) =====
function montarPilulas() {
  const barra = document.getElementById("pilulas");
  barra.innerHTML = "";
  ["Todos", ...categorias].forEach(cat => {
    const b = criar("button", "pilula", cat);
    b.type = "button";
    b.setAttribute("aria-pressed", filtro.categoria === cat ? "true" : "false");
    b.addEventListener("click", () => {
      filtro.categoria = cat;
      atualizarTudo();
      document.getElementById("todos").scrollIntoView();
    });
    barra.appendChild(b);
  });
}

// ===== Blocos "Navegue por categoria" =====
function montarBlocosCategoria() {
  const area = document.getElementById("blocos-categoria");
  categorias.forEach(cat => {
    const b = criar("button", "bloco-categoria");
    b.type = "button";
    const icone = criar("span", "bloco-icone");
    icone.innerHTML = svgIcone(cat);
    b.appendChild(icone);
    b.appendChild(criar("span", "", cat));
    const qtd = produtos.filter(p => p.categoria === cat).length;
    b.appendChild(criar("small", "", qtd + (qtd === 1 ? " produto" : " produtos")));
    b.addEventListener("click", () => {
      filtro.categoria = cat;
      atualizarTudo();
      document.getElementById("todos").scrollIntoView();
    });
    area.appendChild(b);
  });
}

// ===== Filtros da lateral =====
function montarFiltrosLaterais() {
  const areaCat = document.getElementById("filtro-categorias");
  const areaLoja = document.getElementById("filtro-lojas");

  ["Todos", ...categorias].forEach(cat => {
    const label = criar("label", "filtro-opcao");
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "categoria";
    input.value = cat;
    input.addEventListener("change", () => {
      filtro.categoria = cat;
      atualizarTudo();
    });
    label.appendChild(input);
    label.appendChild(document.createTextNode(" " + cat));
    areaCat.appendChild(label);
  });

  lojas.forEach(loja => {
    const label = criar("label", "filtro-opcao");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = loja;
    input.addEventListener("change", () => {
      filtro.lojas = [...areaLoja.querySelectorAll("input:checked")].map(i => i.value);
      atualizarTudo();
    });
    label.appendChild(input);
    label.appendChild(document.createTextNode(" " + loja));
    areaLoja.appendChild(label);
  });
}

// ===== Aplica busca, filtros e ordem =====
function produtosFiltrados() {
  const termo = semAcento(filtro.busca.trim());

  let lista = produtos.filter(p => {
    if (filtro.categoria !== "Todos" && p.categoria !== filtro.categoria) return false;
    if (filtro.lojas.length && !filtro.lojas.includes(p.loja)) return false;
    if (filtro.soFavoritos && !favoritos.includes(p.nome)) return false;
    if (termo && !semAcento(p.nome + " " + p.loja + " " + p.categoria).includes(termo)) return false;
    return true;
  });

  if (filtro.ordem === "menor-preco") lista.sort((a, b) => a.preco - b.preco);
  if (filtro.ordem === "maior-preco") lista.sort((a, b) => b.preco - a.preco);
  if (filtro.ordem === "desconto") lista.sort((a, b) => desconto(b) - desconto(a));

  return lista;
}

// ===== Redesenha a página com o filtro atual =====
function atualizarTudo() {
  // Destaques
  const destaques = document.getElementById("grade-destaques");
  destaques.innerHTML = "";
  produtos.filter(p => p.destaque).slice(0, 4).forEach(p => destaques.appendChild(cardProduto(p)));

  // Todos os achados
  const lista = produtosFiltrados();
  const grade = document.getElementById("grade-todos");
  grade.innerHTML = "";
  lista.forEach(p => grade.appendChild(cardProduto(p)));

  document.getElementById("contador").textContent =
    lista.length + (lista.length === 1 ? " produto encontrado" : " produtos encontrados");
  document.getElementById("sem-resultado").hidden = lista.length > 0;

  // Marca a categoria escolhida nas pílulas e na lateral
  montarPilulas();
  document.querySelectorAll('input[name="categoria"]').forEach(i => {
    i.checked = i.value === filtro.categoria;
  });

  document.getElementById("botao-favoritos").setAttribute("aria-pressed", filtro.soFavoritos ? "true" : "false");
}

// ===== Liga os controles =====
document.getElementById("busca").addEventListener("input", e => {
  filtro.busca = e.target.value;
  atualizarTudo();
});

document.getElementById("form-busca").addEventListener("submit", e => {
  e.preventDefault();
  document.getElementById("todos").scrollIntoView();
});

document.getElementById("ordem").addEventListener("change", e => {
  filtro.ordem = e.target.value;
  atualizarTudo();
});

document.getElementById("botao-favoritos").addEventListener("click", () => {
  filtro.soFavoritos = !filtro.soFavoritos;
  atualizarTudo();
});

document.getElementById("limpar-filtros").addEventListener("click", () => {
  filtro.categoria = "Todos";
  filtro.lojas = [];
  filtro.busca = "";
  filtro.soFavoritos = false;
  document.getElementById("busca").value = "";
  document.querySelectorAll("#filtro-lojas input").forEach(i => (i.checked = false));
  atualizarTudo();
});

// ===== Início =====
document.getElementById("total-produtos").textContent = produtos.length;
document.getElementById("total-lojas").textContent = lojas.length;
montarBlocosCategoria();
montarFiltrosLaterais();

// Se veio da página inicial (ex.: achados.html#cozinha), já abre na categoria
const doLink = semAcento(decodeURIComponent(location.hash.replace("#", "")));
const categoriaDoLink = categorias.find(c => semAcento(c) === doLink);
if (categoriaDoLink) filtro.categoria = categoriaDoLink;

atualizarTudo();

if (categoriaDoLink) {
  document.getElementById("todos").scrollIntoView();
}

"""
Núcleo do Painel Grovan: ler anúncios, ler e gravar o produtos.js e publicar no GitHub.
As telas (painel.py) só chamam estas funções.
"""

import base64
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

CABECALHO_PADRAO = """/*
  Lista de produtos da página Achados.
  Este arquivo é gerado pelo Painel Grovan, mas também pode ser editado à mão.
*/

"""


# =====================================================================
# Números e textos
# =====================================================================
def texto_para_numero(texto):
    """Transforma 'R$ 1.299,90' ou '1299.90' em 1299.9."""
    if texto is None:
        return None
    texto = re.sub(r"[^\d,\.]", "", str(texto).strip())
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return round(float(texto), 2)
    except ValueError:
        return None


def em_reais(valor):
    texto = f"{valor or 0:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + texto


def descobrir_loja(url):
    url = (url or "").lower()
    if "shopee" in url or "shope.ee" in url or "shp.ee" in url:
        return "Shopee"
    if "mercadolivre" in url or "mercadolibre" in url or "meli.la" in url:
        return "Mercado Livre"
    if "amazon" in url or "amzn" in url:
        return "Amazon"
    if "magazineluiza" in url or "magalu" in url:
        return "Magalu"
    return "Loja"


# =====================================================================
# Ler o anúncio
# =====================================================================
def ler_dados_da_pagina(html):
    sopa = BeautifulSoup(html, "html.parser")
    dados = {"nome": None, "imagem": None, "preco": None, "precoAntigo": None}

    def meta(*nomes):
        for nome in nomes:
            tag = sopa.find("meta", attrs={"property": nome}) or sopa.find("meta", attrs={"name": nome})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return None

    dados["nome"] = meta("og:title", "twitter:title")
    dados["imagem"] = meta("og:image", "twitter:image")
    # Preço "oficial" do produto (às vezes é o preço cheio, sem a promoção)
    preco_estruturado = texto_para_numero(meta("product:price:amount", "og:price:amount"))

    for bloco in sopa.find_all("script", type="application/ld+json"):
        try:
            conteudo = json.loads(bloco.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        itens = conteudo if isinstance(conteudo, list) else [conteudo]
        for item in itens:
            if isinstance(item, dict) and "@graph" in item:
                itens.extend(item["@graph"])
                continue
            if not isinstance(item, dict) or item.get("@type") != "Product":
                continue
            dados["nome"] = dados["nome"] or item.get("name")
            imagem = item.get("image")
            if isinstance(imagem, list):
                imagem = imagem[0] if imagem else None
            if isinstance(imagem, dict):
                imagem = imagem.get("url")
            dados["imagem"] = dados["imagem"] or imagem
            ofertas = item.get("offers") or {}
            if isinstance(ofertas, list):
                ofertas = ofertas[0] if ofertas else {}
            preco_estruturado = preco_estruturado or texto_para_numero(ofertas.get("price") or ofertas.get("lowPrice"))

    if preco_estruturado is None:
        tag = sopa.find(attrs={"itemprop": "price"})
        if tag:
            preco_estruturado = texto_para_numero(tag.get("content") or tag.get_text())

    # ----- Preço que aparece na tela (é aqui que fica a PROMOÇÃO) -----
    def valor_ml(seletor):
        """Preço do Mercado Livre: junta reais e centavos."""
        reais = sopa.select_one(seletor + " .andes-money-amount__fraction")
        if not reais:
            return None
        centavos = reais.find_next_sibling(class_="andes-money-amount__cents")
        return texto_para_numero(reais.get_text() + ("," + centavos.get_text() if centavos else ""))

    def valor_texto(*seletores):
        """Preço de outras lojas: pega o primeiro seletor que existir."""
        for seletor in seletores:
            tag = sopa.select_one(seletor)
            if tag:
                valor = texto_para_numero(tag.get("content") or tag.get_text())
                if valor:
                    return valor
        return None

    preco_promocional = (
        # Mercado Livre: o preço grande do anúncio (não pega o riscado nem as parcelas)
        valor_ml(".ui-pdp-price__second-line")
        # Amazon: o preço a pagar
        or valor_texto(".priceToPay .a-offscreen", "#corePrice_feature_div .a-price .a-offscreen", "#priceblock_dealprice", "#priceblock_ourprice")
        # Magalu e outras lojas que marcam o preço na tela
        or valor_texto('[data-testid="price-value"]', '[data-testid="price-final"]', ".price-final", ".sale-price")
    )

    preco_riscado = (
        valor_ml("s.andes-money-amount--previous")
        or valor_texto(".basisPrice .a-offscreen", ".a-text-price .a-offscreen", '[data-testid="price-original"]', ".old-price", "del")
    )

    # O preço atual é o promocional; se não achar na tela, usa o oficial
    dados["preco"] = preco_promocional or preco_estruturado
    dados["precoAntigo"] = preco_riscado
    # Se o preço oficial for maior que o promocional e não houver preço riscado, ele vira o "antes"
    if not dados["precoAntigo"] and preco_estruturado and dados["preco"] and preco_estruturado > dados["preco"]:
        dados["precoAntigo"] = preco_estruturado
    # Preço antigo só faz sentido se for maior que o atual
    if dados["precoAntigo"] and dados["preco"] and dados["precoAntigo"] <= dados["preco"]:
        dados["precoAntigo"] = None
    dados["precoPromocional"] = bool(preco_promocional)

    if dados["nome"]:
        dados["nome"] = re.split(r"\s+[|\-–]\s+(Mercado Livre|Shopee|Amazon)", dados["nome"])[0].strip()
    return dados


# ----- Shopee -----
ERROS_SHOPEE = {
    10020: "A Shopee recusou a assinatura: confira o App ID e o Segredo em Configurações (sem espaços no começo ou no fim).",
    10035: "Sua conta de afiliado ainda não tem acesso à API. Peça a liberação no painel de afiliados da Shopee.",
    10030: "Muitas consultas seguidas na API da Shopee. Espere um minuto e tente de novo.",
    10010: "A Shopee não entendeu a consulta (erro 10010). Me mande um print desta mensagem.",
    11001: "A Shopee recusou os dados do produto (erro 11001). Confira se o link é de um produto.",
    10000: "A API da Shopee está instável agora. Tente de novo em alguns minutos.",
}

PADROES_SHOPEE = [
    r"-i\.(\d+)\.(\d+)",                       # .../nome-do-produto-i.LOJA.ITEM
    r"/(?:product|opaanlp|universal-link/product)/(\d+)/(\d+)",
    r"[?&]shopid=(\d+).*?[?&]itemid=(\d+)",
    r'"shopid"\s*:\s*(\d+).*?"itemid"\s*:\s*(\d+)',
]


class ErroShopee(Exception):
    """Erro da API da Shopee com mensagem amigável."""


def ids_shopee(texto):
    """Procura (loja, item) num endereço ou num pedaço de página. Devolve None se não achar."""
    from urllib.parse import unquote
    for _ in range(3):  # links dentro de links vêm codificados (%2F...)
        texto = unquote(texto)
    for padrao in PADROES_SHOPEE:
        achado = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        if achado:
            return achado.group(1), achado.group(2)
    return None


def link_curto_shopee(url):
    return bool(re.search(r"(s\.shopee\.com\.br|shope\.ee|shp\.ee)/", url or "", re.IGNORECASE))


def abrir_link_curto(url):
    """Segue os redirecionamentos um a um e devolve todos os endereços pelo caminho.
    Assim acha o produto mesmo se a última página for de login ou verificação."""
    enderecos, atual = [url], url
    for _ in range(8):
        try:
            resposta = requests.get(atual, headers=CABECALHOS, timeout=20, allow_redirects=False)
        except requests.RequestException:
            break
        destino = resposta.headers.get("Location")
        if resposta.is_redirect and destino:
            atual = requests.compat.urljoin(atual, destino)
            enderecos.append(atual)
            continue
        # Alguns links redirecionam pela própria página (JavaScript ou meta refresh)
        enderecos.append(resposta.text[:200000])
        break
    return enderecos


def consultar_api_shopee(consulta, config):
    """Faz a chamada assinada à API de afiliados. Devolve o 'data' ou levanta ErroShopee."""
    app_id = (config.get("shopee_app_id") or "").strip()
    segredo = (config.get("shopee_segredo") or "").strip()
    corpo = json.dumps({"query": consulta}, separators=(",", ":"))
    momento = str(int(time.time()))
    assinatura = hashlib.sha256((app_id + momento + corpo + segredo).encode("utf-8")).hexdigest()
    try:
        resposta = requests.post(
            "https://open-api.affiliate.shopee.com.br/graphql",
            data=corpo.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"SHA256 Credential={app_id}, Timestamp={momento}, Signature={assinatura}",
            },
            timeout=20,
        )
    except requests.RequestException:
        raise ErroShopee("Sem conexão com a API da Shopee. Confira a internet.")
    try:
        dados = resposta.json()
    except ValueError:
        raise ErroShopee(f"A API da Shopee respondeu com erro {resposta.status_code}.")
    erros = dados.get("errors") or []
    if erros:
        extra = erros[0].get("extensions") or {}
        codigo = extra.get("code")
        try:
            codigo = int(codigo)
        except (TypeError, ValueError):
            pass
        original = extra.get("message") or erros[0].get("message") or ""
        texto = ERROS_SHOPEE.get(codigo) or f"A Shopee respondeu: {original} (código {codigo})."
        if codigo == 10000 and original:
            texto += f" Detalhe da Shopee: {original}"
        if dados.get("data") is None or not any((dados.get("data") or {}).values()):
            raise ErroShopee(texto)
    return dados.get("data") or {}


def buscar_na_api_shopee(loja_id, item_id, config):
    consulta = (
        "{ productOfferV2(shopId: %s, itemId: %s, limit: 1) { nodes "
        "{ productName imageUrl priceMin priceMax priceDiscountRate offerLink productLink } } }"
        % (int(loja_id), int(item_id))
    )
    nos = (consultar_api_shopee(consulta, config).get("productOfferV2") or {}).get("nodes") or []
    if not nos:
        raise ErroShopee("A Shopee não achou esse produto no programa de afiliados (pode estar sem comissão ou fora do ar).")
    item = nos[0]
    preco = texto_para_numero(item.get("priceMin"))
    antigo = None
    try:
        desconto = float(item.get("priceDiscountRate") or 0)
    except (TypeError, ValueError):
        desconto = 0
    if preco and 0 < desconto < 100:
        antigo = round(preco / (1 - desconto / 100), 2)
    return {
        "nome": item.get("productName"),
        "imagem": item.get("imageUrl"),
        "preco": preco,
        "precoAntigo": antigo,
        "precoPromocional": bool(antigo),
        "link": item.get("offerLink"),
        "linkProduto": item.get("productLink"),
    }


def gerar_link_afiliado_shopee(url_produto, config):
    """Gera o seu link curto de afiliado (s.shopee.com.br/...) para qualquer produto. None se falhar."""
    if not url_produto:
        return None
    url = url_produto.split("?")[0].replace("\\", "").replace('"', "")
    consulta = 'mutation { generateShortLink(input: {originUrl: "%s", subIds: ["grovan"]}) { shortLink } }' % url
    try:
        dados = consultar_api_shopee(consulta, config)
    except ErroShopee:
        return None
    return (dados.get("generateShortLink") or {}).get("shortLink")


def testar_api_shopee(config):
    """Usado no botão 'Testar' das Configurações. Devolve (deu_certo, texto)."""
    if not config.get("shopee_app_id") or not config.get("shopee_segredo"):
        return False, "Preencha o App ID e o Segredo da Shopee."
    try:
        dados = consultar_api_shopee('{ productOfferV2(keyword: "fone", limit: 1) { nodes { productName } } }', config)
    except ErroShopee as erro:
        return False, str(erro)
    nos = (dados.get("productOfferV2") or {}).get("nodes") or []
    return True, "API da Shopee funcionando!" + (f" Exemplo: {nos[0]['productName'][:60]}" if nos else "")


def ler_produto_mercado_livre(url, html):
    """Links de afiliado do ML abrem uma vitrine. Acha o código do anúncio (MLB...) e lê a página do produto."""
    texto = requests.utils.unquote(url) + " " + (html or "")[:400000]
    enderecos = []
    catalogo = re.search(r"/p/(MLB\d{6,})", texto)
    if catalogo:
        enderecos.append(f"https://www.mercadolivre.com.br/p/{catalogo.group(1)}")
    anuncio = re.search(r"MLB-?(\d{6,})", texto)
    if anuncio:
        enderecos.append(f"https://produto.mercadolivre.com.br/MLB-{anuncio.group(1)}")
    for endereco in enderecos:
        if endereco == url:
            continue
        try:
            resposta = requests.get(endereco, headers=CABECALHOS, timeout=20)
        except requests.RequestException:
            continue
        if resposta.status_code == 200:
            dados = ler_dados_da_pagina(resposta.text)
            if dados.get("preco"):
                return dados
    return None


def buscar_anuncio(link, config):
    """Lê um anúncio e devolve um dicionário com loja, nome, imagem, preços e aviso."""
    loja = descobrir_loja(link)
    if not str(link or "").lower().startswith(("http://", "https://")):
        return {"loja": loja, "nome": None, "imagem": None, "preco": None, "precoAntigo": None, "precoPromocional": False,
                "link": link, "shopee": "", "aviso": "Esse produto está sem link de anúncio."}
    resultado = {"loja": loja, "nome": None, "imagem": None, "preco": None, "precoAntigo": None, "precoPromocional": False,
                 "link": link, "shopee": "", "aviso": ""}

    # ----- Shopee: usa a API de afiliados (a página da Shopee não deixa ler os dados) -----
    if loja == "Shopee":
        tem_api = config.get("shopee_app_id") and config.get("shopee_segredo")
        ids = ids_shopee(link)
        if not ids and link_curto_shopee(link):
            for endereco in abrir_link_curto(link):
                ids = ids_shopee(endereco)
                if ids:
                    break
        if not tem_api:
            resultado["aviso"] = "A Shopee não deixa ler a página. Preencha o App ID e o Segredo da API em Configurações para buscar automaticamente."
            return resultado
        if not ids:
            resultado["aviso"] = ("A Shopee não mostrou qual é o produto por trás desse link curto. "
                                  "Use a busca \"Procurar na Shopee\" abaixo (pelo nome do produto) ou cole o endereço "
                                  "da página do produto, aquele que aparece no navegador.")
            return resultado
        try:
            dados = buscar_na_api_shopee(ids[0], ids[1], config)
        except ErroShopee as erro:
            resultado["aviso"] = str(erro)
            return resultado
        resultado["shopee"] = f"{ids[0]}.{ids[1]}"
        link_de_afiliado = dados.pop("link", None)
        link_produto = dados.pop("linkProduto", None)
        resultado.update({k: v for k, v in dados.items() if v})
        # O link curto que você colou já é o seu link de afiliado: mantém ele.
        # Se colou o link normal da página, gera o seu link curto de afiliado.
        if not link_curto_shopee(link):
            resultado["link"] = (gerar_link_afiliado_shopee(link_produto or link, config)
                                 or link_de_afiliado or link)
        return resultado

    try:
        resposta = requests.get(link, headers=CABECALHOS, timeout=20, allow_redirects=True)
        resposta.raise_for_status()
        if "charset" not in resposta.headers.get("Content-Type", "").lower():
            resposta.encoding = resposta.apparent_encoding
        loja_final = descobrir_loja(resposta.url)
        if loja == "Loja":
            resultado["loja"] = loja_final
        if loja_final == "Shopee":
            return buscar_anuncio(resposta.url, config) | {"link": link}
        dados = ler_dados_da_pagina(resposta.text)
        if not dados.get("preco") and resultado["loja"] == "Mercado Livre":
            dados = ler_produto_mercado_livre(resposta.url, resposta.text) or dados
        resultado.update({k: v for k, v in dados.items() if v})
    except requests.RequestException as erro:
        resultado["aviso"] = f"Não consegui abrir o link ({erro.__class__.__name__}). Preencha os campos manualmente."
        return resultado

    if not any(resultado.get(c) for c in ("nome", "imagem", "preco")):
        resultado["aviso"] = "A loja não deixou ler os dados automaticamente. Preencha os campos manualmente."
    return resultado


# =====================================================================
# produtos.js
# =====================================================================
def caminho_produtos(pasta_site):
    return Path(pasta_site) / "js" / "produtos.js"


def ler_produtos(pasta_site):
    arquivo = caminho_produtos(pasta_site)
    return interpretar_produtos(arquivo.read_text(encoding="utf-8"))


def interpretar_produtos(conteudo):
    """Transforma o texto do produtos.js em (comentário do topo, lista de produtos)."""
    inicio = conteudo.find("const produtos")
    if inicio == -1:
        raise ValueError("Não encontrei 'const produtos' em js/produtos.js")
    cabecalho = conteudo[:inicio] or CABECALHO_PADRAO
    lista_js = conteudo[conteudo.find("[", inicio): conteudo.rfind("]") + 1]
    lista_json = re.sub(r'(\n\s*)(\w+)\s*:', r'\1"\2":', lista_js)
    lista_json = re.sub(r",(\s*[}\]])", r"\1", lista_json)
    return cabecalho, json.loads(lista_json)


def montar_bloco(p):
    def texto(valor):
        return json.dumps(valor or "", ensure_ascii=False)

    return (
        "  {\n"
        f"    nome: {texto(p['nome'])},\n"
        f"    loja: {texto(p['loja'])},\n"
        f"    categoria: {texto(p['categoria'])},\n"
        f"    link: {texto(p['link'])},\n"
        f"    imagem: {texto(p.get('imagem'))},\n"
        f"    preco: {float(p['preco'] or 0):.2f},\n"
        f"    precoAntigo: {float(p.get('precoAntigo') or 0):.2f},\n"
        f"    destaque: {'true' if p.get('destaque') else 'false'}"
        # Código do produto na Shopee (LOJA.ITEM): deixa o painel conferir o preço pela API
        + (f",\n    shopee: {texto(p['shopee'])}\n" if p.get("shopee") else "\n")
        + "  },\n"
    )


def gerar_texto(cabecalho, produtos):
    """Monta o texto completo do produtos.js."""
    corpo = "".join(montar_bloco(p) for p in produtos)
    return cabecalho + "const produtos = [\n" + corpo + "];\n"


def gravar_produtos(pasta_site, cabecalho, produtos):
    caminho_produtos(pasta_site).write_text(gerar_texto(cabecalho, produtos), encoding="utf-8")


# =====================================================================
# banners.js (ordem, tempo e banners com imagem própria)
# =====================================================================
CAMINHO_PRODUTOS = "js/produtos.js"
CAMINHO_BANNERS = "js/banners.js"
PASTA_IMAGENS_BANNER = "img/banners"
SEGUNDOS_PADRAO = 5

CABECALHO_BANNERS = """/*
  Banner rotativo da página Achados.
  Este arquivo é gerado pelo Painel Grovan (tela Banners).

  configBanner.segundos -> quanto tempo cada banner fica na tela
  banners -> a ordem do banner. Dois tipos:
    { tipo: "produto", nome: "..." }  -> um produto marcado com estrela (destaque)
    { tipo: "imagem", titulo, imagem, imagemCelular, link, ativo } -> arte própria
  Produtos com estrela que não estiverem na lista entram no final.
*/

"""


def interpretar_banners(texto):
    """Lê o banners.js. Devolve (config, lista). Se o arquivo não existe, devolve o padrão."""
    config, lista = {"segundos": SEGUNDOS_PADRAO}, []
    if not texto:
        return config, lista
    marca_config = texto.find("const configBanner")
    marca_lista = texto.find("const banners")
    if marca_config != -1:
        trecho = texto[texto.find("{", marca_config): (marca_lista if marca_lista > marca_config else len(texto))]
        trecho = trecho[: trecho.rfind("}") + 1]
        try:
            config.update(json.loads(trecho))
        except json.JSONDecodeError:
            pass
    if marca_lista != -1:
        trecho = texto[texto.find("[", marca_lista): texto.rfind("]") + 1]
        try:
            lista = json.loads(trecho)
        except json.JSONDecodeError:
            lista = []
    return config, [b for b in lista if isinstance(b, dict)]


def gerar_banners(config, lista):
    return (
        CABECALHO_BANNERS
        + "const configBanner = " + json.dumps(config, ensure_ascii=False) + ";\n\n"
        + "const banners = " + json.dumps(lista, ensure_ascii=False, indent=2) + ";\n"
    )


def banners_na_tela(lista, produtos):
    """Junta a lista salva com os produtos de estrela, na ordem em que aparecem no site.
    Cada item volta com 'tipo' e, se for produto, o próprio produto em 'produto'."""
    destaques = {p["nome"]: p for p in produtos if p.get("destaque")}
    usados, resultado = set(), []
    for item in lista:
        if item.get("tipo") == "produto":
            nome = item.get("nome")
            if nome in destaques and nome not in usados:
                usados.add(nome)
                resultado.append({"tipo": "produto", "nome": nome, "produto": destaques[nome]})
        elif item.get("tipo") == "imagem":
            resultado.append(dict(item))
    for nome, produto in destaques.items():
        if nome not in usados:
            resultado.append({"tipo": "produto", "nome": nome, "produto": produto})
    return resultado


def limpar_para_salvar(itens):
    """Tira o que é só da tela (o produto inteiro) antes de gravar."""
    saida = []
    for item in itens:
        if item.get("tipo") == "produto":
            saida.append({"tipo": "produto", "nome": item["nome"]})
        else:
            saida.append({
                "tipo": "imagem",
                "titulo": item.get("titulo", ""),
                "imagem": item.get("imagem", ""),
                "imagemCelular": item.get("imagemCelular", ""),
                "link": item.get("link", ""),
                "ativo": bool(item.get("ativo", True)),
            })
    return saida


# =====================================================================
# Onde os arquivos ficam guardados: pasta local OU direto no GitHub
# =====================================================================
class ErroArmazenamento(Exception):
    """Erro com uma mensagem amigável para mostrar na tela."""


class ArmazenamentoLocal:
    """Lê e grava os arquivos numa pasta do computador (precisa publicar depois)."""

    publica_direto = False

    def __init__(self, pasta):
        self.pasta = pasta

    def _caminho(self, caminho):
        return Path(self.pasta) / caminho

    def ler_texto(self, caminho, opcional=False):
        arquivo = self._caminho(caminho)
        if not arquivo.exists():
            if opcional:
                return None
            raise ErroArmazenamento(f"Não encontrei {caminho} na pasta do site.")
        return arquivo.read_text(encoding="utf-8")

    def ler_binario(self, caminho):
        arquivo = self._caminho(caminho)
        return arquivo.read_bytes() if arquivo.exists() else None

    def gravar_bytes(self, caminho, dados, mensagem):
        arquivo = self._caminho(caminho)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_bytes(dados)

    # Produtos
    def ler(self):
        return interpretar_produtos(self.ler_texto(CAMINHO_PRODUTOS))

    def gravar(self, cabecalho, produtos, mensagem):
        self.gravar_bytes(CAMINHO_PRODUTOS, gerar_texto(cabecalho, produtos).encode("utf-8"), mensagem)

    # Banners
    def ler_banners(self):
        return interpretar_banners(self.ler_texto(CAMINHO_BANNERS, opcional=True))

    def gravar_banners(self, config, lista, mensagem):
        self.gravar_bytes(CAMINHO_BANNERS, gerar_banners(config, lista).encode("utf-8"), mensagem)


class ArmazenamentoGitHub:
    """Lê e grava os arquivos direto no repositório do GitHub, pela API."""

    publica_direto = True
    CAMINHO = CAMINHO_PRODUTOS

    def __init__(self, repositorio, token, ramo="main", api="https://api.github.com"):
        self.base = f"{api.rstrip('/')}/repos/{repositorio.strip('/')}/contents/"
        self.endereco = self.base + CAMINHO_PRODUTOS
        self.ramo = ramo or "main"
        self.cabecalhos = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._shas = {}  # "versão" de cada arquivo: o GitHub exige para alterar

    def _erro(self, resposta, caminho=CAMINHO_PRODUTOS):
        if resposta.status_code == 401:
            return ErroArmazenamento("O GitHub recusou a chave de acesso (token). Confira o token em Configurações.")
        if resposta.status_code == 403:
            return ErroArmazenamento("O token não tem permissão para alterar o repositório. Confira as permissões (Contents: Read and write).")
        if resposta.status_code == 404:
            return ErroArmazenamento(f"Não encontrei o repositório ou o arquivo {caminho}. Confira o nome do repositório e se o token tem acesso a ele.")
        if resposta.status_code == 409:
            return ErroArmazenamento("O arquivo foi alterado em outro lugar ao mesmo tempo. Recarregue a página e tente de novo.")
        if resposta.status_code == 422:
            return ErroArmazenamento("O GitHub não aceitou o arquivo. Se for imagem, tente uma menor (até 5 MB).")
        return ErroArmazenamento(f"O GitHub respondeu com erro {resposta.status_code}.")

    def _get(self, caminho, **extra):
        try:
            return requests.get(self.base + caminho, params={"ref": self.ramo}, timeout=30, **extra)
        except requests.RequestException:
            raise ErroArmazenamento("Sem conexão com o GitHub. Confira a internet.")

    def ler_texto(self, caminho, opcional=False):
        resposta = self._get(caminho, headers=self.cabecalhos)
        if resposta.status_code == 404 and opcional:
            self._shas[caminho] = None
            return None
        if resposta.status_code != 200:
            raise self._erro(resposta, caminho)
        dados = resposta.json()
        self._shas[caminho] = dados["sha"]
        return base64.b64decode(dados["content"]).decode("utf-8")

    def ler_binario(self, caminho):
        resposta = self._get(caminho, headers={**self.cabecalhos, "Accept": "application/vnd.github.raw+json"})
        return resposta.content if resposta.status_code == 200 else None

    def gravar_bytes(self, caminho, dados, mensagem):
        if caminho not in self._shas:
            resposta = self._get(caminho, headers=self.cabecalhos)
            if resposta.status_code == 200:
                self._shas[caminho] = resposta.json()["sha"]
            elif resposta.status_code == 404:
                self._shas[caminho] = None  # arquivo novo
            else:
                raise self._erro(resposta, caminho)
        corpo = {
            "message": mensagem,
            "content": base64.b64encode(dados).decode("ascii"),
            "branch": self.ramo,
        }
        if self._shas.get(caminho):
            corpo["sha"] = self._shas[caminho]
        try:
            resposta = requests.put(self.base + caminho, headers=self.cabecalhos, json=corpo, timeout=60)
        except requests.RequestException:
            raise ErroArmazenamento("Sem conexão com o GitHub. Nada foi salvo.")
        if resposta.status_code not in (200, 201):
            raise self._erro(resposta, caminho)
        self._shas[caminho] = resposta.json()["content"]["sha"]

    # Produtos
    def ler(self):
        return interpretar_produtos(self.ler_texto(CAMINHO_PRODUTOS))

    def gravar(self, cabecalho, produtos, mensagem):
        self.gravar_bytes(CAMINHO_PRODUTOS, gerar_texto(cabecalho, produtos).encode("utf-8"), mensagem)

    # Banners
    def ler_banners(self):
        return interpretar_banners(self.ler_texto(CAMINHO_BANNERS, opcional=True))

    def gravar_banners(self, config, lista, mensagem):
        self.gravar_bytes(CAMINHO_BANNERS, gerar_banners(config, lista).encode("utf-8"), mensagem)


# =====================================================================
# Git / GitHub
# =====================================================================
def rodar_git(pasta_site, *argumentos):
    return subprocess.run(["git", *argumentos], cwd=pasta_site, capture_output=True, text=True)


def mudancas_pendentes(pasta_site):
    """True se produtos, banners ou imagens têm alterações ainda não publicadas."""
    resultado = rodar_git(pasta_site, "status", "--porcelain", "--", "js", "img")
    return resultado.returncode == 0 and bool(resultado.stdout.strip())


def publicar(pasta_site, mensagem):
    """Faz pull, commit e push. Devolve (deu_certo, texto)."""
    passos = [
        ("pull", "--no-edit"),
        ("add", "-A", "--", "js", "img"),
        ("commit", "-m", mensagem),
        ("push",),
    ]
    for passo in passos:
        resultado = rodar_git(pasta_site, *passo)
        if resultado.returncode != 0:
            saida = (resultado.stderr or resultado.stdout).strip()
            if passo[0] == "commit" and "nothing to commit" in saida:
                return True, "Nada novo para publicar."
            return False, f"Erro no git {passo[0]}: {saida}"
    return True, "Publicado! O site atualiza em 1 a 2 minutos."

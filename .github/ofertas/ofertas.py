"""
Procura de ofertas dos produtos da página Achados.

Para cada produto:
  1. Confere o próprio link: o preço (promocional) mudou?
  2. Procura o mesmo produto mais barato em outros anúncios
     (Shopee pela API de afiliados, Mercado Livre pela busca pública).

Usado em dois lugares:
  - no painel (botão "Procurar agora");
  - no GitHub Actions, uma vez por dia, mesmo com o painel fechado.
"""

import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import requests

import nucleo

CAMINHO_OFERTAS = ".github/ofertas/ofertas.json"
CAMINHO_IGNORADOS = ".github/ofertas/ignorados.json"

# Só sugere se ficar pelo menos 3% e R$ 1,00 mais barato
ECONOMIA_MINIMA_PCT = 3
ECONOMIA_MINIMA_REAIS = 1.0
# Quão parecido o nome precisa ser para considerar "o mesmo produto" (0 a 1)
SEMELHANCA_MINIMA = 0.55
ALTERNATIVAS_POR_PRODUTO = 3

PALAVRAS_VAZIAS = {
    "de", "da", "do", "das", "dos", "e", "com", "para", "pra", "em", "a", "o", "as", "os",
    "kit", "novo", "nova", "original", "promocao", "oferta", "frete", "gratis", "envio",
    "imediato", "pronta", "entrega", "un", "und", "unidade", "unidades", "cor", "cores",
}


def agora_brasil():
    return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------
# Comparar nomes de produtos
# ---------------------------------------------------------------------
def palavras(nome):
    texto = unicodedata.normalize("NFD", (nome or "").lower()).encode("ascii", "ignore").decode()
    lista = re.findall(r"[a-z0-9]+", texto)
    return {p for p in lista if p not in PALAVRAS_VAZIAS and (len(p) > 1 or p.isdigit())}


def semelhanca(nome_a, nome_b):
    """0 a 1: quanto das palavras do produto original aparecem no outro anúncio.
    Números (110v, 5l, 1200w) pesam o dobro: mudam o produto."""
    a, b = palavras(nome_a), palavras(nome_b)
    if not a or not b:
        return 0.0
    peso = lambda conj: sum(2 if any(c.isdigit() for c in p) else 1 for p in conj)
    return peso(a & b) / peso(a)


def termo_de_busca(nome, maximo=7):
    """As primeiras palavras importantes do nome viram o texto da busca."""
    texto = unicodedata.normalize("NFD", nome or "").encode("ascii", "ignore").decode()
    lista = [p for p in re.findall(r"[A-Za-z0-9]+", texto) if p.lower() not in PALAVRAS_VAZIAS]
    return " ".join(lista[:maximo])


def vale_a_pena(preco_novo, preco_atual):
    if not preco_novo or not preco_atual:
        return False
    economia = preco_atual - preco_novo
    return economia >= ECONOMIA_MINIMA_REAIS and economia / preco_atual * 100 >= ECONOMIA_MINIMA_PCT


# ---------------------------------------------------------------------
# Onde procurar
# ---------------------------------------------------------------------
def procurar_na_shopee(termo, config, limite=20):
    """Busca por nome na API de afiliados. O link já vem como SEU link de afiliado."""
    if not (config.get("shopee_app_id") and config.get("shopee_segredo")):
        return []
    termo = termo.replace("\\", " ").replace('"', " ")
    consultas = [
        '{ productOfferV2(keyword: "%s", limit: %d) { nodes '
        "{ itemId shopId productName imageUrl priceMin priceDiscountRate offerLink productLink "
        "shopName commissionRate sales } } }" % (termo, limite),
        # Plano B: só o essencial (a API às vezes recusa alguns campos)
        '{ productOfferV2(keyword: "%s", limit: %d) { nodes '
        "{ itemId shopId productName imageUrl priceMin offerLink productLink } } }" % (termo, limite),
    ]
    for numero, consulta in enumerate(consultas):
        try:
            dados = nucleo.consultar_api_shopee(consulta, config)
            break
        except nucleo.ErroShopee:
            if numero == len(consultas) - 1:
                raise
            time.sleep(1)
    resultado = []
    for item in (dados.get("productOfferV2") or {}).get("nodes") or []:
        preco = nucleo.texto_para_numero(item.get("priceMin"))
        if not preco:
            continue
        try:
            desconto = float(item.get("priceDiscountRate") or 0)
        except (TypeError, ValueError):
            desconto = 0
        try:
            comissao = round(float(item.get("commissionRate") or 0) * 100, 1)
        except (TypeError, ValueError):
            comissao = 0
        resultado.append({
            "loja": "Shopee",
            "shopee": f"{item.get('shopId')}.{item.get('itemId')}" if item.get("shopId") and item.get("itemId") else "",
            "nome": item.get("productName") or "",
            "preco": preco,
            "precoAntigo": round(preco / (1 - desconto / 100), 2) if 0 < desconto < 100 else None,
            "imagem": item.get("imageUrl") or "",
            "link": item.get("offerLink") or item.get("productLink") or "",
            "linkProduto": item.get("productLink") or "",
            "afiliado": bool(item.get("offerLink")),
            "vendedor": item.get("shopName") or "",
            "comissao": comissao,
            "vendas": item.get("sales") or 0,
        })
    return resultado


def procurar_no_mercado_livre(termo, limite=20):
    """Busca pública do Mercado Livre. Se o ML pedir login, devolve vazio (sem erro)."""
    try:
        resposta = requests.get(
            "https://api.mercadolibre.com/sites/MLB/search",
            params={"q": termo, "limit": limite},
            headers={"User-Agent": nucleo.CABECALHOS["User-Agent"]},
            timeout=20,
        )
    except requests.RequestException:
        return []
    if resposta.status_code != 200:
        return []
    resultado = []
    for item in resposta.json().get("results") or []:
        preco = item.get("price")
        if not preco:
            continue
        antigo = item.get("original_price")
        resultado.append({
            "loja": "Mercado Livre",
            "nome": item.get("title") or "",
            "preco": float(preco),
            "precoAntigo": float(antigo) if antigo and antigo > preco else None,
            "imagem": (item.get("thumbnail") or "").replace("http://", "https://").replace("-I.jpg", "-O.jpg"),
            "link": item.get("permalink") or "",
            "linkProduto": item.get("permalink") or "",
            "afiliado": False,  # precisa gerar o link de afiliado no portal do ML
            "vendedor": "",
            "comissao": None,
            "vendas": item.get("sold_quantity") or 0,
        })
    return resultado


# ---------------------------------------------------------------------
# Procura completa
# ---------------------------------------------------------------------
def conferir_preco(produto, config):
    """Lê de novo o link do produto e compara o preço promocional."""
    codigo = produto.get("shopee") or ""
    try:
        if "." in codigo and config.get("shopee_app_id") and config.get("shopee_segredo"):
            # Produto da Shopee com código salvo: confere direto na API (não depende do link curto)
            loja_id, item_id = codigo.split(".", 1)
            dados = nucleo.buscar_na_api_shopee(loja_id, item_id, config)
        else:
            dados = nucleo.buscar_anuncio(produto["link"], config)
            if not dados.get("preco") and dados.get("loja") == "Shopee" and not codigo:
                dados["aviso"] = ("Esse produto da Shopee foi salvo só com o link curto. Abra Editar, use "
                                  "\"Procurar na Shopee\" uma vez e salve: daí em diante o preço é conferido sozinho.")
    except nucleo.ErroShopee as erro:
        return {"status": "erro", "texto": str(erro)}
    except Exception as erro:  # nunca deixa um produto travar a procura toda
        return {"status": "erro", "texto": f"Não consegui conferir ({erro.__class__.__name__})."}
    preco_novo = dados.get("preco")
    if not preco_novo:
        return {"status": "erro", "texto": dados.get("aviso") or "A loja não mostrou o preço."}
    preco_atual = float(produto.get("preco") or 0)
    if abs(preco_novo - preco_atual) < 0.01:
        return {"status": "igual", "preco": preco_novo}
    return {
        "status": "baixou" if preco_novo < preco_atual else "subiu",
        "preco": preco_novo,
        "precoAntigo": dados.get("precoAntigo"),
        "imagem": dados.get("imagem") or "",
    }


def procurar_alternativas(produto, config, ignorados=()):
    termo = termo_de_busca(produto["nome"])
    if not termo:
        return [], []
    candidatos, avisos = [], []
    for tentativa in range(3):
        try:
            candidatos += procurar_na_shopee(termo, config)
            break
        except nucleo.ErroShopee as erro:
            if tentativa == 2:
                avisos.append(str(erro))
            else:
                time.sleep(3 * (tentativa + 1))  # a Shopee costuma voltar depois de alguns segundos
    candidatos += procurar_no_mercado_livre(termo)

    preco_atual = float(produto.get("preco") or 0)
    meus_links = {produto.get("link")}
    vistos, bons = set(), []
    for c in candidatos:
        chave = c["linkProduto"] or c["link"]
        if not c["link"] or chave in vistos or c["link"] in meus_links or chave in ignorados or c["link"] in ignorados:
            continue
        vistos.add(chave)
        nota = semelhanca(produto["nome"], c["nome"])
        if nota < SEMELHANCA_MINIMA or not vale_a_pena(c["preco"], preco_atual):
            continue
        c["semelhanca"] = round(nota * 100)
        c["economia"] = round(preco_atual - c["preco"], 2)
        bons.append(c)
    # Mais parecido primeiro; empate: mais barato
    bons.sort(key=lambda c: (-c["semelhanca"], c["preco"]))
    return bons[:ALTERNATIVAS_POR_PRODUTO], avisos


def procurar_tudo(produtos, config, ignorados=(), progresso=None, pausa=1.0):
    """Procura ofertas para todos os produtos. Devolve o relatório para gravar em ofertas.json."""
    itens, falhas_shopee, motivo = [], [], ""
    produtos = [p for p in produtos if str(p.get("link", "")).lower().startswith(("http://", "https://"))]
    for numero, produto in enumerate(produtos, start=1):
        if progresso:
            progresso(numero, len(produtos), produto["nome"])
        preco = conferir_preco(produto, config)
        alternativas, avisos = procurar_alternativas(produto, config, set(ignorados))
        if avisos:
            falhas_shopee.append(produto["nome"])
            motivo = avisos[0]
        itens.append({
            "nome": produto["nome"],
            "link": produto["link"],
            "loja": produto.get("loja", ""),
            "precoAtual": float(produto.get("preco") or 0),
            "conferencia": preco,
            "alternativas": alternativas,
        })
        time.sleep(pausa)  # não sobrecarregar as lojas
    avisos_gerais = []
    if falhas_shopee:
        avisos_gerais.append(
            f"A Shopee não respondeu na busca de {len(falhas_shopee)} de {len(itens)} produtos "
            f"({', '.join(falhas_shopee[:3])}{'...' if len(falhas_shopee) > 3 else ''}). "
            f"Esses produtos são procurados de novo na próxima procura. Motivo: {motivo}"
        )
    return {"geradoEm": agora_brasil(), "itens": itens, "avisos": avisos_gerais}


def chave_preco_mantido(link, preco):
    return f"preco|{link}|{float(preco):.2f}"


def resumo(relatorio, produtos, ignorados=()):
    """Junta o relatório com os produtos atuais (ignora o que já foi trocado ou removido)."""
    ignorados = set(ignorados)
    por_link = {p["link"]: (i, p) for i, p in enumerate(produtos)}
    cartoes = []
    for item in (relatorio or {}).get("itens", []):
        if item["link"] not in por_link:
            continue  # produto já foi trocado ou removido
        indice, produto = por_link[item["link"]]
        conf = item.get("conferencia") or {}
        mudou = (conf.get("status") in ("baixou", "subiu")
                 and abs(float(conf.get("preco") or 0) - float(produto.get("preco") or 0)) >= 0.01
                 and chave_preco_mantido(produto["link"], conf.get("preco") or 0) not in ignorados)
        alternativas = [a for a in item.get("alternativas", [])
                        if vale_a_pena(a["preco"], float(produto.get("preco") or 0)) and a["link"] not in ignorados]
        if mudou or alternativas or conf.get("status") == "erro":
            cartoes.append({"indice": indice, "produto": produto, "conferencia": conf if mudou or conf.get("status") == "erro" else None,
                            "alternativas": alternativas})
    # Primeiro quem tem novidade de verdade; erros por último
    cartoes.sort(key=lambda c: (not (c["alternativas"] or c["conferencia"] and c["conferencia"]["status"] != "erro"),))
    return cartoes


def contar_novidades(cartoes):
    return sum(1 for c in cartoes if c["alternativas"] or (c["conferencia"] and c["conferencia"]["status"] != "erro"))

"""
BOT DE ACHADOS DA GROVAN
========================
Cola o link de um anúncio, o bot lê nome, foto e preço,
e adiciona o produto em js/produtos.js (a página de Achados atualiza sozinha).

Como usar (no terminal do VS Code, dentro da pasta do site):
    python bot_achados.py

Instalar as bibliotecas (só na primeira vez):
    pip install requests beautifulsoup4
"""

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Faltam bibliotecas. Rode no terminal:  pip install requests beautifulsoup4")
    sys.exit(1)


# ===== Configurações =====
PASTA = Path(__file__).parent
ARQUIVO_PRODUTOS = PASTA / "js" / "produtos.js"
ARQUIVO_CONFIG = PASTA / "bot_config.json"  # credenciais da API da Shopee (opcional)

# Cabeçalhos para o site achar que é um navegador comum
CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


# =====================================================================
# 1. DESCOBRIR A LOJA
# =====================================================================
def descobrir_loja(url):
    """Diz qual é a loja olhando o endereço do link."""
    url = url.lower()
    if "shopee" in url:
        return "Shopee"
    if "mercadolivre" in url or "mercadolibre" in url or "meli.la" in url:
        return "Mercado Livre"
    if "amazon" in url or "amzn" in url:
        return "Amazon"
    if "magazineluiza" in url or "magalu" in url:
        return "Magalu"
    return "Loja"


# =====================================================================
# 2. LER A PÁGINA DO ANÚNCIO
# =====================================================================
def baixar_pagina(url):
    """Abre o link (seguindo redirecionamentos) e devolve (endereço final, HTML)."""
    resposta = requests.get(url, headers=CABECALHOS, timeout=20, allow_redirects=True)
    resposta.raise_for_status()
    # Se a loja não informar a codificação, descobre pelo conteúdo (evita "ElÃ©trica")
    if "charset" not in resposta.headers.get("Content-Type", "").lower():
        resposta.encoding = resposta.apparent_encoding
    return resposta.url, resposta.text


def texto_para_numero(texto):
    """Transforma 'R$ 1.299,90' ou '1299.90' em 1299.9."""
    if texto is None:
        return None
    texto = str(texto).strip()
    texto = re.sub(r"[^\d,\.]", "", texto)
    if not texto:
        return None
    if "," in texto:  # formato brasileiro: 1.299,90
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return round(float(texto), 2)
    except ValueError:
        return None


def ler_dados_da_pagina(html):
    """Procura nome, imagem e preço nas informações que as lojas deixam na página."""
    sopa = BeautifulSoup(html, "html.parser")
    dados = {"nome": None, "imagem": None, "preco": None, "precoAntigo": None}

    def meta(*nomes):
        for nome in nomes:
            tag = sopa.find("meta", attrs={"property": nome}) or sopa.find("meta", attrs={"name": nome})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return None

    # a) Etiquetas "Open Graph" (as mesmas usadas na prévia do WhatsApp)
    dados["nome"] = meta("og:title", "twitter:title")
    dados["imagem"] = meta("og:image", "twitter:image")
    dados["preco"] = texto_para_numero(meta("product:price:amount", "og:price:amount"))

    # b) Dados estruturados (JSON-LD), usados por muitas lojas
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
            preco = ofertas.get("price") or ofertas.get("lowPrice")
            dados["preco"] = dados["preco"] or texto_para_numero(preco)

    # c) Preço marcado com itemprop="price"
    if dados["preco"] is None:
        tag = sopa.find(attrs={"itemprop": "price"})
        if tag:
            dados["preco"] = texto_para_numero(tag.get("content") or tag.get_text())

    # d) Preço antigo do Mercado Livre (o valor riscado)
    riscado = sopa.select_one("s.andes-money-amount--previous .andes-money-amount__fraction")
    if riscado:
        centavos = riscado.find_next_sibling(class_="andes-money-amount__cents")
        valor = riscado.get_text() + ("," + centavos.get_text() if centavos else "")
        dados["precoAntigo"] = texto_para_numero(valor)

    # Limpa o nome (algumas lojas colocam " | Mercado Livre" no final)
    if dados["nome"]:
        dados["nome"] = re.split(r"\s+[|\-–]\s+(Mercado Livre|Shopee|Amazon)", dados["nome"])[0].strip()

    return dados


# =====================================================================
# 3. SHOPEE: API OFICIAL DE AFILIADOS (opcional)
# =====================================================================
def ids_da_shopee(url):
    """Tira o shopId e o itemId de um link da Shopee (formatos -i.LOJA.ITEM ou /product/LOJA/ITEM)."""
    achado = re.search(r"-i\.(\d+)\.(\d+)", url) or re.search(r"/product/(\d+)/(\d+)", url)
    if achado:
        return achado.group(1), achado.group(2)
    return None, None


def buscar_na_api_shopee(url):
    """Consulta a API de afiliados da Shopee. Precisa do bot_config.json com app_id e segredo."""
    if not ARQUIVO_CONFIG.exists():
        return None
    config = json.loads(ARQUIVO_CONFIG.read_text(encoding="utf-8"))
    app_id = config.get("shopee_app_id")
    segredo = config.get("shopee_segredo")
    if not app_id or not segredo:
        return None

    loja_id, item_id = ids_da_shopee(url)
    if not item_id:
        return None

    consulta = {
        "query": (
            "{ productOfferV2(shopId: %s, itemId: %s) { nodes { "
            "productName imageUrl priceMin priceMax offerLink } } }" % (loja_id, item_id)
        )
    }
    corpo = json.dumps(consulta, separators=(",", ":"))
    momento = str(int(time.time()))
    assinatura = hashlib.sha256((app_id + momento + corpo + segredo).encode()).hexdigest()

    resposta = requests.post(
        "https://open-api.affiliate.shopee.com.br/graphql",
        data=corpo,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={app_id}, Timestamp={momento}, Signature={assinatura}",
        },
        timeout=20,
    )
    resposta.raise_for_status()
    nos = resposta.json().get("data", {}).get("productOfferV2", {}).get("nodes", [])
    if not nos:
        return None
    item = nos[0]
    return {
        "nome": item.get("productName"),
        "imagem": item.get("imageUrl"),
        "preco": texto_para_numero(item.get("priceMin")),
        "precoAntigo": None,
        "link": item.get("offerLink"),  # já vem como seu link de afiliado
    }


# =====================================================================
# 4. CONVERSAR COM VOCÊ NO TERMINAL
# =====================================================================
def perguntar(texto, padrao=None):
    """Faz uma pergunta. Se apertar Enter sem digitar, usa o valor padrão."""
    sugestao = f" [{padrao}]" if padrao not in (None, "") else ""
    resposta = input(f"{texto}{sugestao}: ").strip()
    return resposta if resposta else padrao


def perguntar_preco(texto, padrao=None):
    while True:
        resposta = perguntar(texto, f"{padrao:.2f}".replace(".", ",") if padrao else None)
        if resposta in (None, "", "0"):
            return 0
        valor = texto_para_numero(resposta)
        if valor is not None:
            return valor
        print("  Digite só o número, por exemplo 49,90")


def categorias_existentes():
    if not ARQUIVO_PRODUTOS.exists():
        return []
    return sorted(set(re.findall(r'categoria:\s*"([^"]+)"', ARQUIVO_PRODUTOS.read_text(encoding="utf-8"))))


# =====================================================================
# 5. GRAVAR NO produtos.js
# =====================================================================
def montar_bloco(produto):
    """Escreve o produto no mesmo formato da lista."""
    def texto(valor):
        return json.dumps(valor or "", ensure_ascii=False)

    return (
        "  {\n"
        f"    nome: {texto(produto['nome'])},\n"
        f"    loja: {texto(produto['loja'])},\n"
        f"    categoria: {texto(produto['categoria'])},\n"
        f"    link: {texto(produto['link'])},\n"
        f"    imagem: {texto(produto['imagem'])},\n"
        f"    preco: {produto['preco']:.2f},\n"
        f"    precoAntigo: {produto['precoAntigo'] or 0:.2f},\n"
        f"    destaque: {'true' if produto['destaque'] else 'false'}\n"
        "  },\n"
    )


def salvar_produto(produto):
    conteudo = ARQUIVO_PRODUTOS.read_text(encoding="utf-8")
    fim = conteudo.rfind("];")
    if fim == -1:
        raise ValueError("Não encontrei o final da lista ( ]; ) em js/produtos.js")
    novo = conteudo[:fim] + montar_bloco(produto) + conteudo[fim:]
    ARQUIVO_PRODUTOS.write_text(novo, encoding="utf-8")


# =====================================================================
# 6. PUBLICAR NO GITHUB
# =====================================================================
def publicar(nomes):
    mensagem = "Novos achados: " + ", ".join(nomes)[:60]
    comandos = [
        ["git", "pull"],
        ["git", "add", "js/produtos.js"],
        ["git", "commit", "-m", mensagem],
        ["git", "push"],
    ]
    for comando in comandos:
        resultado = subprocess.run(comando, cwd=PASTA, capture_output=True, text=True)
        if resultado.returncode != 0:
            print("  Erro ao rodar:", " ".join(comando))
            print(" ", (resultado.stderr or resultado.stdout).strip())
            print("  Os produtos foram salvos. Publique pelo VS Code (Commit e Sync Changes).")
            return
    print("  Publicado! O site atualiza em 1 a 2 minutos.")


# =====================================================================
# 7. FLUXO PRINCIPAL
# =====================================================================
def adicionar_um_produto():
    link = perguntar("\nCole o link do anúncio (ou Enter para sair)")
    if not link:
        return None

    loja = descobrir_loja(link)
    dados = None
    print(f"  Loja: {loja}. Lendo o anúncio...")

    # Shopee: tenta primeiro a API oficial
    if loja == "Shopee":
        try:
            dados = buscar_na_api_shopee(link)
        except requests.RequestException as erro:
            print(f"  A API da Shopee não respondeu ({erro}).")

    # Outras lojas (ou Shopee sem API): lê a página
    if not dados:
        try:
            endereco_final, html = baixar_pagina(link)
            if loja == "Shopee" and not dados:
                dados = buscar_na_api_shopee(endereco_final) if ARQUIVO_CONFIG.exists() else None
            dados = dados or ler_dados_da_pagina(html)
        except requests.RequestException as erro:
            print(f"  Não consegui abrir o link ({erro}). Vamos preencher na mão.")
            dados = {"nome": None, "imagem": None, "preco": None, "precoAntigo": None}

    encontrou = [campo for campo in ("nome", "imagem", "preco") if dados.get(campo)]
    if encontrou:
        print("  Encontrei:", ", ".join(encontrou), "— confira e aperte Enter para manter.")
    else:
        print("  A loja não deixou ler os dados automaticamente. Preencha abaixo.")

    # Confirma ou corrige cada informação
    nome = perguntar("Nome do produto", dados.get("nome"))
    while not nome:
        nome = perguntar("O nome é obrigatório. Nome do produto")
    imagem = perguntar("Link da imagem (Enter para deixar sem)", dados.get("imagem")) or ""
    preco = perguntar_preco("Preço atual", dados.get("preco"))
    preco_antigo = perguntar_preco("Preço antigo, riscado (Enter ou 0 se não tiver)", dados.get("precoAntigo"))

    existentes = categorias_existentes()
    if existentes:
        print("  Categorias:", ", ".join(existentes))
    categoria = perguntar("Categoria", existentes[0] if existentes else "Casa")
    destaque = (perguntar("É destaque? (s/n)", "n") or "n").lower().startswith("s")

    produto = {
        "nome": nome,
        "loja": loja,
        "categoria": categoria,
        "link": dados.get("link") or link,
        "imagem": imagem,
        "preco": preco,
        "precoAntigo": preco_antigo if preco_antigo > preco else 0,
        "destaque": destaque,
    }
    salvar_produto(produto)
    print(f"  ✓ '{nome}' adicionado em js/produtos.js")
    return nome


def main():
    print("=" * 50)
    print("  BOT DE ACHADOS DA GROVAN")
    print("=" * 50)
    if not ARQUIVO_PRODUTOS.exists():
        print("Não encontrei js/produtos.js. Rode o bot dentro da pasta do site.")
        return

    adicionados = []
    while True:
        nome = adicionar_um_produto()
        if not nome:
            break
        adicionados.append(nome)

    if not adicionados:
        print("Nenhum produto adicionado.")
        return

    print(f"\n{len(adicionados)} produto(s) adicionado(s).")
    if (perguntar("Publicar no site agora? (s/n)", "s") or "s").lower().startswith("s"):
        publicar(adicionados)
    else:
        print("Ok! Quando quiser, publique pelo VS Code (Commit e Sync Changes).")


if __name__ == "__main__":
    main()

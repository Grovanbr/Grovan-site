"""
Roda no GitHub Actions todo dia (arquivo .github/workflows/ofertas.yml).
Lê os produtos do site, procura ofertas e grava .github/ofertas/ofertas.json.

As chaves da Shopee vêm dos "secrets" do repositório (SHOPEE_APP_ID e SHOPEE_SEGREDO).
nucleo.py e ofertas.py são cópias dos arquivos do Painel Grovan.
"""
import json
import os
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
RAIZ = PASTA.parent.parent          # raiz do repositório do site
sys.path.insert(0, str(PASTA))

import nucleo   # noqa: E402
import ofertas  # noqa: E402

config = {
    "shopee_app_id": os.environ.get("SHOPEE_APP_ID", "").strip(),
    "shopee_segredo": os.environ.get("SHOPEE_SEGREDO", "").strip(),
}

cabecalho, produtos = nucleo.ler_produtos(RAIZ)

arquivo_ignorados = RAIZ / ofertas.CAMINHO_IGNORADOS
ignorados = json.loads(arquivo_ignorados.read_text(encoding="utf-8")) if arquivo_ignorados.exists() else []


def progresso(atual, total, nome):
    print(f"[{atual}/{total}] {nome}", flush=True)


relatorio = ofertas.procurar_tudo(produtos, config, ignorados, progresso=progresso, pausa=2.0)
if not config["shopee_app_id"]:
    relatorio["avisos"].append("A procura diária está sem as chaves da Shopee: cadastre SHOPEE_APP_ID e SHOPEE_SEGREDO nos secrets do repositório.")

# Preço acompanha o anúncio: atualiza o js/produtos.js do site
mudancas = ofertas.aplicar_precos(produtos, relatorio, ignorados)
if mudancas:
    nucleo.gravar_produtos(RAIZ, cabecalho, produtos)
    for m in mudancas:
        print(f"Preço atualizado: {m['nome']}: {m['de']:.2f} -> {m['para']:.2f}")

saida = RAIZ / ofertas.CAMINHO_OFERTAS
saida.parent.mkdir(parents=True, exist_ok=True)
saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")

novidades = sum(1 for i in relatorio["itens"] if i["alternativas"] or i["conferencia"].get("status") in ("baixou", "subiu"))
print(f"Pronto: {len(produtos)} produtos conferidos, {novidades} com novidade.")

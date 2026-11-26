"""Salva print e HTML da página quando um teste E2E falha.

Com isso, quem investiga a falha (inclusive no GitHub Actions, onde não dá para
ver o navegador) vê exatamente o que o navegador mostrava naquele momento.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def nome_de_arquivo_seguro(nome):
    """'test_lista[chrome]' -> 'test_lista_chrome_'. Mantém letras (com acento),
    números, ponto, hífen e sublinhado; o resto vira '_' (inclusive '/')."""
    return re.sub(r"[^\w.-]", "_", nome)


def salvar_evidencias(navegador, pasta, nome_do_teste):
    """Salva <nome>.png e <nome>.html em `pasta` e devolve os caminhos salvos.

    Nunca levanta exceção: se o navegador já fechou, registra no log e devolve
    lista vazia, para não esconder o motivo original da falha do teste.
    """
    pasta = Path(pasta)
    base = nome_de_arquivo_seguro(nome_do_teste)
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        png = pasta / f"{base}.png"
        html = pasta / f"{base}.html"
        navegador.save_screenshot(str(png))
        html.write_text(navegador.page_source, encoding="utf-8")
        return [png, html]
    except Exception as erro:
        logger.warning("Não foi possível salvar as evidências de %s: %s", nome_do_teste, erro)
        return []

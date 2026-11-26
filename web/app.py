"""Página Flask que lista as notícias coletadas pelo main.py.

Rodar localmente:  python -m web.app   (abre em http://127.0.0.1:5000)

A página só LÊ o dados/noticias.json; quem coleta é o main.py.
"""

import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request

from config.temas import TEMAS
from core.exportador import carregar_json
from core.modelo import NAO_INFORMADO
from web.filtros import aplicar_filtros, filtros_validos, opcoes_de_filtro

PASTA_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_PADRAO = PASTA_PROJETO / "dados" / "noticias.json"

ROTULOS_DE_ORIGEM = {"primaria": "primária", "comunidade": "comunidade"}

# Content-Security-Policy: o navegador só carrega o CSS do próprio site e não
# executa nenhum script. Mesmo que um título malicioso escapasse do Jinja, o
# navegador bloquearia o script. É uma segunda camada de proteção.
CSP = ("default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; "
       "form-action 'self'; frame-ancestors 'none'")

logger = logging.getLogger(__name__)


def formatar_data(valor):
    """'2026-11-16T10:30:00+00:00' -> '16/11/2026 10:30 UTC'."""
    if valor == NAO_INFORMADO:
        return "data não informada"
    try:
        return datetime.fromisoformat(valor).strftime("%d/%m/%Y %H:%M UTC")
    except (TypeError, ValueError):
        return valor  # mostra como veio, em vez de quebrar a página


def criar_app(caminho_json=CAMINHO_PADRAO, temas=TEMAS):
    """Cria o app apontando para um JSON. Os testes passam um JSON fictício
    e temas próprios, para não depender da config real."""
    app = Flask(__name__)
    caminho_json = Path(caminho_json)

    app.jinja_env.filters["data_br"] = formatar_data
    app.jinja_env.globals["ROTULOS_DE_ORIGEM"] = ROTULOS_DE_ORIGEM
    app.jinja_env.globals["NOMES_DOS_FILTROS"] = {
        "origem": "Origem", "fonte": "Fonte", "idioma": "Idioma", "tema": "Tema"}

    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        resposta.headers["Content-Security-Policy"] = CSP
        # Impede o navegador de "adivinhar" o tipo do arquivo.
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        return resposta

    @app.get("/")
    def lista():
        try:
            noticias = carregar_json(caminho_json)
        except Exception:
            # Detalhes vão só para o log; a página mostra uma mensagem simples.
            logger.exception("Não foi possível ler %s", caminho_json)
            return render_template("noticias.html", erro=True, noticias=[],
                                   total=0, opcoes=None, filtros={}), 500

        # Os filtros vêm da URL (?origem=...&tema=...). Valores desconhecidos
        # são ignorados, para ninguém quebrar a página editando o endereço.
        opcoes = opcoes_de_filtro(noticias, temas)
        filtros = filtros_validos(request.args, opcoes)
        return render_template("noticias.html", erro=False,
                               noticias=aplicar_filtros(noticias, filtros, temas),
                               total=len(noticias), opcoes=opcoes, filtros=filtros)

    return app


if __name__ == "__main__":
    # 127.0.0.1: só este computador acessa. debug=False: o modo debug permite
    # executar código pelo navegador e nunca deve ficar ligado sem necessidade.
    criar_app().run(host="127.0.0.1", port=5000, debug=False)

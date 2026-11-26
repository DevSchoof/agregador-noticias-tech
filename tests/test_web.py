"""Testes da página Flask SEM navegador, com o test client do Flask.

O test client faz requisições direto ao app (sem servidor, sem rede). Cada teste
grava um JSON fictício na pasta temporária do pytest e aponta o app para ele.
"""

import pytest

from core.exportador import salvar_json
from core.modelo import NAO_INFORMADO, Noticia
from web.app import criar_app


def noticia(titulo="Python fictício 9.9", link="https://exemplo.com/a", origem="primaria",
            **outros):
    campos = dict(fonte="Fonte Fictícia", data_publicacao="2026-11-16T10:30:00+00:00",
                  idioma="en")
    campos.update(outros)
    return Noticia(titulo=titulo, link=link, origem=origem, **campos)


@pytest.fixture
def abrir(tmp_path):
    """Grava as notícias num JSON temporário e devolve a resposta de GET /."""
    def _abrir(noticias=None, conteudo_bruto=None):
        caminho = tmp_path / "noticias.json"
        if conteudo_bruto is not None:
            caminho.write_text(conteudo_bruto, encoding="utf-8")
        elif noticias is not None:
            salvar_json(noticias, caminho)
        app = criar_app(caminho)
        app.config["TESTING"] = True
        return app.test_client().get("/")
    return _abrir


def html(resposta):
    return resposta.get_data(as_text=True)


# ------------------------------------------------------------- lista

def test_mostra_cada_noticia_com_seus_campos(abrir):
    resposta = abrir([noticia(tags=["releases"])])
    texto = html(resposta)

    assert resposta.status_code == 200
    assert texto.count('data-testid="noticia"') == 1
    assert "Python fictício 9.9" in texto
    assert 'href="https://exemplo.com/a"' in texto
    assert "Fonte Fictícia" in texto
    assert "16/11/2026 10:30 UTC" in texto
    assert 'data-testid="idioma">en<' in texto
    assert 'data-testid="origem">primária<' in texto


def test_link_abre_em_nova_aba_com_protecao(abrir):
    texto = html(abrir([noticia()]))

    assert 'target="_blank"' in texto
    assert 'rel="noopener noreferrer"' in texto


def test_mantem_a_ordem_do_json(abrir):
    # O JSON já vem ordenado pelo deduplicador; a página não reordena.
    texto = html(abrir([noticia("Primeira", "https://exemplo.com/1"),
                        noticia("Segunda", "https://exemplo.com/2"),
                        noticia("Terceira", "https://exemplo.com/3")]))

    assert texto.index("Primeira") < texto.index("Segunda") < texto.index("Terceira")


def test_mostra_o_total(abrir):
    texto = html(abrir([noticia("A", "https://exemplo.com/1"),
                        noticia("B", "https://exemplo.com/2")]))

    assert 'data-testid="total">2 notícias<' in texto


def test_total_no_singular(abrir):
    assert 'data-testid="total">1 notícia<' in html(abrir([noticia()]))


def test_etiqueta_de_comunidade(abrir):
    texto = html(abrir([noticia(origem="comunidade")]))

    assert 'data-testid="origem">comunidade<' in texto


def test_aviso_de_provavel_duplicata(abrir):
    texto = html(abrir([
        noticia("Mesmo título", "https://exemplo.com/1"),
        noticia("Mesmo título", "https://exemplo.com/2", origem="comunidade",
                provavel_duplicata_de="https://exemplo.com/1"),
    ]))

    assert texto.count('data-testid="duplicata"') == 1
    assert 'href="https://exemplo.com/1"' in texto


def test_campos_nao_informados(abrir):
    texto = html(abrir([noticia(data_publicacao=NAO_INFORMADO, resumo=NAO_INFORMADO)]))

    assert "data não informada" in texto
    assert 'data-testid="resumo"' not in texto  # sem resumo, sem parágrafo vazio


def test_mostra_o_resumo_quando_existe(abrir):
    texto = html(abrir([noticia(resumo="Um resumo curto e fictício.")]))

    assert 'data-testid="resumo">Um resumo curto e fictício.<' in texto


# ------------------------------------------------------- lista vazia

def test_json_vazio_mostra_mensagem(abrir):
    texto = html(abrir([]))

    assert 'data-testid="vazio"' in texto
    assert 'data-testid="noticia"' not in texto


def test_arquivo_inexistente_mostra_mensagem(abrir):
    resposta = abrir()  # nenhum arquivo gravado

    assert resposta.status_code == 200
    assert 'data-testid="vazio"' in html(resposta)


def test_json_corrompido_mostra_erro_sem_detalhes_internos(abrir):
    resposta = abrir(conteudo_bruto="[{ isto não é json")
    texto = html(resposta)

    assert resposta.status_code == 500
    assert 'data-testid="erro"' in texto
    assert "Traceback" not in texto and "JSONDecodeError" not in texto


# -------------------------------------------------------- segurança

def test_titulo_com_html_aparece_como_texto(abrir):
    # O título vem de terceiros: o Jinja escapa, e o <script> não executa.
    texto = html(abrir([noticia(titulo='<script>alert("x")</script> & <b>negrito</b>')]))

    assert "<script>alert" not in texto
    assert "&lt;script&gt;" in texto
    assert "<b>negrito</b>" not in texto


def test_cabecalhos_de_seguranca(abrir):
    resposta = abrir([noticia()])

    # CSP: só carrega recursos do próprio site; nenhum script.
    assert resposta.headers["Content-Security-Policy"] == (
        "default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'")
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"


def test_pagina_em_utf8_e_portugues(abrir):
    resposta = abrir([noticia()])

    assert resposta.headers["Content-Type"] == "text/html; charset=utf-8"
    assert '<html lang="pt-BR">' in html(resposta)


def test_css_e_servido(tmp_path):
    cliente = criar_app(tmp_path / "noticias.json").test_client()

    resposta = cliente.get("/static/estilo.css")

    assert resposta.status_code == 200
    assert resposta.mimetype == "text/css"

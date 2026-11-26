"""Testes E2E da página de notícias, com o padrão Page Object.

Os testes dizem O QUE verificar; a classe PaginaNoticias (paginas.py) sabe COMO
mexer na página. Se o HTML mudar, só a classe muda.

Dados fictícios (conftest.py), na ordem da página:
  1. Python 9.9 fictício lançado      Blog Fictício        en  primária    python
  2. Selenium 9.0 fictício            Releases Fictícias   en  primária    automação
  3. Novo modelo de AI fictício       Fórum Fictício       en  comunidade  ia
  4. Automação com Python no Brasil   Portal Fictício      pt  comunidade  python, automação
"""

import pytest

from tests.e2e.paginas import PaginaNoticias

pytestmark = pytest.mark.e2e

PYTHON_9 = "Python 9.9 fictício lançado"
SELENIUM_9 = "Selenium 9.0 fictício"
MODELO_AI = "Novo modelo de AI fictício"
AUTOMACAO_BR = "Automação com Python no Brasil"
TODAS = [PYTHON_9, SELENIUM_9, MODELO_AI, AUTOMACAO_BR]


@pytest.fixture
def pagina(navegador, servidor):
    """Abre a página do zero em cada teste (o navegador é compartilhado)."""
    return PaginaNoticias(navegador, servidor).abrir()


# ------------------------------------------------------------- lista

def test_lista_completa_na_ordem(pagina):
    assert pagina.titulos() == TODAS
    assert pagina.total() == "4 notícias"


def test_filtros_comecam_em_todos(pagina):
    for campo in ("origem", "fonte", "idioma", "tema"):
        assert pagina.filtro_selecionado(campo) == ""


# ----------------------------------------------------------- filtros

@pytest.mark.parametrize("campo, valor, esperados", [
    ("origem", "comunidade", [MODELO_AI, AUTOMACAO_BR]),
    ("fonte", "Releases Fictícias", [SELENIUM_9]),
    ("idioma", "pt", [AUTOMACAO_BR]),
    ("tema", "python", [PYTHON_9, AUTOMACAO_BR]),
    ("tema", "automacao", [SELENIUM_9, AUTOMACAO_BR]),
    ("tema", "ia", [MODELO_AI]),
])
def test_um_filtro_por_vez(pagina, campo, valor, esperados):
    pagina.filtrar(**{campo: valor})

    assert pagina.titulos() == esperados
    assert pagina.total() == f"{len(esperados)} de 4 notícias"


def test_filtros_combinados(pagina):
    pagina.filtrar(origem="comunidade", tema="python")

    assert pagina.titulos() == [AUTOMACAO_BR]


def test_filtro_escolhido_continua_selecionado(pagina):
    pagina.filtrar(fonte="Fórum Fictício", tema="ia")

    assert pagina.filtro_selecionado("fonte") == "Fórum Fictício"
    assert pagina.filtro_selecionado("tema") == "ia"
    assert pagina.filtro_selecionado("origem") == ""


def test_filtro_vai_para_a_url(pagina):
    # Permite compartilhar um filtro mandando o link.
    pagina.filtrar(origem="comunidade")

    assert "origem=comunidade" in pagina.url()


def test_filtro_sem_resultado_mostra_mensagem(pagina):
    pagina.filtrar(fonte="Blog Fictício", tema="ia")

    assert pagina.titulos() == []
    assert "Nenhuma notícia com esses filtros" in pagina.mensagem_sem_resultado()


def test_limpar_filtros_volta_para_a_lista_completa(pagina):
    pagina.filtrar(origem="comunidade", idioma="pt")
    pagina.limpar_filtros()

    assert pagina.titulos() == TODAS
    assert pagina.filtro_selecionado("origem") == ""


def test_abrir_com_filtro_na_url(navegador, servidor):
    pagina = PaginaNoticias(navegador, servidor).abrir("/?tema=ia")

    assert pagina.titulos() == [MODELO_AI]
    assert pagina.filtro_selecionado("tema") == "ia"


# ------------------------------------------------------------- links

def test_link_aponta_para_o_original_em_nova_aba(pagina):
    # Não clicamos: o link leva a um site externo, e os testes não usam a internet.
    link = pagina.link_de(PYTHON_9)

    assert link["href"] == "https://exemplo.com/1"
    assert link["target"] == "_blank"
    assert set(link["rel"].split()) == {"noopener", "noreferrer"}


def test_etiqueta_de_origem_de_cada_noticia(pagina):
    assert pagina.origens() == ["primária", "primária", "comunidade", "comunidade"]

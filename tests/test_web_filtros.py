"""Testes da lógica pura dos filtros da página (sem Flask, sem navegador)."""

from itertools import count

import pytest

from core.modelo import Noticia
from web.filtros import aplicar_filtros, filtros_validos, opcoes_de_filtro

TEMAS = {
    "pt": {"python": ["python"], "ia": ["ia", "inteligência artificial"]},
    "en": {"python": ["python"], "ia": ["ai"]},
}


_numeros = count(1)  # gera 1, 2, 3... para cada notícia ter um link diferente


def noticia(titulo, fonte="Blog A", idioma="en", origem="primaria"):
    return Noticia(titulo=titulo, link=f"https://exemplo.com/{next(_numeros)}",
                   fonte=fonte, idioma=idioma, origem=origem)


@pytest.fixture
def noticias():
    return [
        noticia("Python 9.9 released", fonte="Blog A"),
        noticia("New AI model", fonte="Blog B"),
        noticia("Python e IA no Brasil", fonte="Portal C", idioma="pt", origem="comunidade"),
        noticia("Preço do café", fonte="Portal C", idioma="pt", origem="comunidade"),
    ]


def titulos(noticias):
    return [n.titulo for n in noticias]


# ------------------------------------------------------------ opções

def test_opcoes_vem_dos_dados_e_da_config(noticias):
    opcoes = opcoes_de_filtro(noticias, TEMAS)

    assert opcoes["origem"] == [("primaria", "primária"), ("comunidade", "comunidade")]
    assert opcoes["fonte"] == [("Blog A", "Blog A"), ("Blog B", "Blog B"),
                               ("Portal C", "Portal C")]  # em ordem alfabética
    assert opcoes["idioma"] == [("en", "inglês"), ("pt", "português")]
    assert opcoes["tema"] == [("python", "Python"), ("ia", "IA")]  # ordem da config


def test_opcoes_sem_noticias(noticias):
    opcoes = opcoes_de_filtro([], TEMAS)

    assert opcoes["fonte"] == [] and opcoes["idioma"] == []
    assert opcoes["tema"] == [("python", "Python"), ("ia", "IA")]


def test_rotulo_de_tema_desconhecido_usa_o_proprio_nome():
    opcoes = opcoes_de_filtro([], {"en": {"seguranca": ["security"]}})

    assert opcoes["tema"] == [("seguranca", "seguranca")]


# ---------------------------------------------- validação dos filtros

def test_filtros_validos_mantem_so_valores_conhecidos(noticias):
    opcoes = opcoes_de_filtro(noticias, TEMAS)
    pedido = {"origem": "primaria", "fonte": "Blog Inexistente", "idioma": "xx",
              "tema": "ia", "outro": "qualquer"}

    assert filtros_validos(pedido, opcoes) == {"origem": "primaria", "tema": "ia"}


def test_filtros_vazios_sao_ignorados(noticias):
    opcoes = opcoes_de_filtro(noticias, TEMAS)

    assert filtros_validos({"origem": "", "fonte": ""}, opcoes) == {}


# ------------------------------------------------------- aplicação

def test_sem_filtros_devolve_tudo(noticias):
    assert aplicar_filtros(noticias, {}, TEMAS) == noticias


def test_filtro_por_origem(noticias):
    assert titulos(aplicar_filtros(noticias, {"origem": "comunidade"}, TEMAS)) == [
        "Python e IA no Brasil", "Preço do café"]


def test_filtro_por_fonte(noticias):
    assert titulos(aplicar_filtros(noticias, {"fonte": "Blog B"}, TEMAS)) == ["New AI model"]


def test_filtro_por_idioma(noticias):
    assert titulos(aplicar_filtros(noticias, {"idioma": "en"}, TEMAS)) == [
        "Python 9.9 released", "New AI model"]


def test_filtro_por_tema_usa_as_palavras_do_idioma_da_noticia(noticias):
    # "ia" casa "New AI model" (en: "ai") e "Python e IA no Brasil" (pt: "ia").
    assert titulos(aplicar_filtros(noticias, {"tema": "ia"}, TEMAS)) == [
        "New AI model", "Python e IA no Brasil"]


def test_filtros_combinados_valem_juntos(noticias):
    filtros = {"tema": "python", "idioma": "pt", "origem": "comunidade"}

    assert titulos(aplicar_filtros(noticias, filtros, TEMAS)) == ["Python e IA no Brasil"]


def test_filtro_sem_resultado(noticias):
    assert aplicar_filtros(noticias, {"fonte": "Blog A", "tema": "ia"}, TEMAS) == []


def test_mantem_a_ordem_original(noticias):
    resultado = aplicar_filtros(noticias, {"tema": "python"}, TEMAS)

    assert titulos(resultado) == ["Python 9.9 released", "Python e IA no Brasil"]

"""Testes do filtro por tema. Usa temas próprios do teste, para não depender da config."""

import pytest

from config.temas import TEMAS
from core.filtro import (descartar_pre_versoes, e_pre_versao, filtrar_por_tema,
                         temas_da_noticia)
from core.modelo import Noticia

TEMAS_TESTE = {
    "pt": {
        "python": ["python"],
        "ia": ["ia", "inteligência artificial"],
    },
    "en": {
        "python": ["python"],
        "ia": ["ai", "machine learning"],
    },
}


def criar_noticia(titulo="Título fictício sem tema", idioma="pt", **outros):
    return Noticia(
        titulo=titulo,
        link=f"https://exemplo.com/{abs(hash(titulo))}",
        fonte="Fonte Fictícia",
        idioma=idioma,
        origem="primaria",
        **outros,
    )


# ------------------------------------------------------- onde procurar

def test_encontra_tema_no_titulo():
    noticia = criar_noticia("Nova versão do Python sai hoje")
    assert temas_da_noticia(noticia, TEMAS_TESTE) == ["python"]


def test_encontra_tema_no_resumo():
    noticia = criar_noticia(resumo="Um texto que fala de Python.")
    assert temas_da_noticia(noticia, TEMAS_TESTE) == ["python"]


def test_encontra_tema_nas_tags():
    noticia = criar_noticia(tags=["linguagens", "Python"])
    assert temas_da_noticia(noticia, TEMAS_TESTE) == ["python"]


def test_sem_tema_devolve_lista_vazia():
    assert temas_da_noticia(criar_noticia(), TEMAS_TESTE) == []


def test_resumo_nao_informado_nao_conta_como_texto():
    temas = {"pt": {"teste": ["não informado"]}}
    noticia = criar_noticia()  # resumo e data ficam "não informado"
    assert temas_da_noticia(noticia, temas) == []


# ---------------------------------------------- como comparar

def test_ignora_maiusculas_e_minusculas():
    assert temas_da_noticia(criar_noticia("PYTHON em alta"), TEMAS_TESTE) == ["python"]


def test_ignora_acentos_no_texto_e_na_palavra_chave():
    noticia = criar_noticia("Inteligencia Artificial na saúde")
    assert temas_da_noticia(noticia, TEMAS_TESTE) == ["ia"]


def test_casa_so_palavra_inteira():
    noticia = criar_noticia("Encontro de pythonistas")
    assert temas_da_noticia(noticia, TEMAS_TESTE) == []


def test_palavra_curta_nao_casa_dentro_de_outra():
    noticia = criar_noticia("Said the main speaker", idioma="en")
    assert temas_da_noticia(noticia, TEMAS_TESTE) == []


def test_expressao_casa_mesmo_com_hifen_ou_pontuacao():
    noticia = criar_noticia("Curso de machine-learning: inscrições abertas", idioma="en")
    assert temas_da_noticia(noticia, TEMAS_TESTE) == ["ia"]


def test_encontra_varios_temas_na_ordem_da_config():
    noticia = criar_noticia("IA escrita em Python")
    assert temas_da_noticia(noticia, TEMAS_TESTE) == ["python", "ia"]


# ---------------------------------------------- idioma

def test_usa_as_palavras_do_idioma_da_noticia():
    # "e aí" vira "e ai" sem acento: em português "ai" não pode ser tema.
    noticia_pt = criar_noticia("E aí, o que muda no aplicativo?", idioma="pt")
    noticia_en = criar_noticia("New AI model released", idioma="en")

    assert temas_da_noticia(noticia_pt, TEMAS_TESTE) == []
    assert temas_da_noticia(noticia_en, TEMAS_TESTE) == ["ia"]


def test_idioma_sem_temas_configurados_nao_casa_nada():
    temas_so_ingles = {"en": TEMAS_TESTE["en"]}
    noticia = criar_noticia("Novidades do Python", idioma="pt")
    assert temas_da_noticia(noticia, temas_so_ingles) == []


# ---------------------------------------------- filtrar_por_tema

def test_filtrar_mantem_so_as_relevantes_na_mesma_ordem():
    relevante_1 = criar_noticia("Python 4 anunciado")
    irrelevante = criar_noticia("Previsão do tempo para amanhã")
    relevante_2 = criar_noticia("Governo lança curso de inteligência artificial")

    resultado = filtrar_por_tema([relevante_1, irrelevante, relevante_2], TEMAS_TESTE)

    assert resultado == [relevante_1, relevante_2]


def test_filtrar_nao_altera_as_noticias():
    noticia = criar_noticia("Python 4 anunciado", tags=["linguagens"])

    filtrar_por_tema([noticia], TEMAS_TESTE)

    assert noticia.tags == ["linguagens"]


def test_filtrar_lista_vazia():
    assert filtrar_por_tema([], TEMAS_TESTE) == []


# ---------------------------------------------- config/temas.py

@pytest.mark.parametrize("idioma", ["pt", "en"])
def test_config_tem_os_quatro_temas_nos_dois_idiomas(idioma):
    assert set(TEMAS[idioma]) == {"python", "automacao", "dados", "ia"}


@pytest.mark.parametrize("idioma", ["pt", "en"])
def test_config_nenhum_tema_sem_palavras(idioma):
    for tema, palavras in TEMAS[idioma].items():
        assert palavras, f"tema {tema!r} ({idioma}) sem palavras-chave"


# ------------------------------------------------ nightly e pré-versões

@pytest.mark.parametrize("titulo", [
    "Nightly",
    "nightly build",
    "10.0.0.dev0",
    "4.0.0a1",
    "3.16.0b2",
    "2.0rc1",
    "1.0.0-rc.1",
    "v2.0.0-beta",
    "Selenium 5.0.0 Beta 1",
    "Python 3.16.0 alpha 2",
    "1.0pre",
    "Preview 7",
    "SNAPSHOT 1.2",
])
def test_reconhece_pre_versao(titulo):
    assert e_pre_versao(titulo)


@pytest.mark.parametrize("titulo", [
    "8.3.4",
    "9.2.0",
    "Selenium 4.54.0",
    "v1.2.3",
    "Python 3.15.2, 3.14.10 and 3.13.18 are out",
    "Release 2026-11-20",
    "Alphabet anuncia novidades",  # "alpha" dentro de outra palavra
    "Betamax 1.0",
    "Development update",          # "dev" como palavra comum
])
def test_versao_estavel_nao_e_pre_versao(titulo):
    assert not e_pre_versao(titulo)


def test_descartar_pre_versoes_mantem_a_ordem():
    noticias = [criar_noticia("Selenium 4.54.0"), criar_noticia("Nightly"),
                criar_noticia("9.2.0"), criar_noticia("10.0.0.dev0")]

    assert [n.titulo for n in descartar_pre_versoes(noticias)] == ["Selenium 4.54.0", "9.2.0"]


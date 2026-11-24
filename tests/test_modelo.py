"""Testes do contrato de dados: a dataclass Noticia."""

import pytest

from core.modelo import NAO_INFORMADO, Noticia


def criar_noticia(**alteracoes):
    """Cria uma Noticia válida com dados fictícios; os testes mudam só o que importa."""
    campos = {
        "titulo": "Biblioteca fictícia lança versão 2.0",
        "link": "https://exemplo.com/noticia-ficticia",
        "fonte": "Fonte Fictícia",
        "idioma": "pt",
        "origem": "primaria",
    }
    campos.update(alteracoes)
    return Noticia(**campos)


def test_cria_noticia_com_campos_obrigatorios():
    noticia = criar_noticia()

    assert noticia.titulo == "Biblioteca fictícia lança versão 2.0"
    assert noticia.link == "https://exemplo.com/noticia-ficticia"
    assert noticia.fonte == "Fonte Fictícia"
    assert noticia.idioma == "pt"
    assert noticia.origem == "primaria"


def test_campos_opcionais_ausentes_viram_nao_informado():
    noticia = criar_noticia()

    assert noticia.data_publicacao == NAO_INFORMADO
    assert noticia.resumo == NAO_INFORMADO


def test_valor_de_nao_informado():
    assert NAO_INFORMADO == "não informado"


def test_area_padrao_e_tech():
    assert criar_noticia().area == "tech"


def test_tags_padrao_e_lista_vazia():
    assert criar_noticia().tags == []


def test_tags_nao_sao_compartilhadas_entre_noticias():
    # Armadilha clássica do Python: lista como valor padrão compartilhada.
    primeira = criar_noticia()
    segunda = criar_noticia()

    primeira.tags.append("python")

    assert segunda.tags == []


def test_tags_none_vira_lista_vazia():
    assert criar_noticia(tags=None).tags == []


@pytest.mark.parametrize("campo", ["titulo", "fonte", "data_publicacao", "resumo"])
@pytest.mark.parametrize("valor_vazio", [None, "", "   "])
def test_texto_vazio_ou_none_vira_nao_informado(campo, valor_vazio):
    noticia = criar_noticia(**{campo: valor_vazio})

    assert getattr(noticia, campo) == NAO_INFORMADO


@pytest.mark.parametrize("origem", ["primaria", "comunidade"])
def test_aceita_origens_validas(origem):
    assert criar_noticia(origem=origem).origem == origem


@pytest.mark.parametrize("origem", ["Primaria", "primária", "blog", "", None])
def test_rejeita_origem_invalida(origem):
    with pytest.raises(ValueError):
        criar_noticia(origem=origem)


@pytest.mark.parametrize("idioma", ["pt", "en"])
def test_aceita_idiomas_validos(idioma):
    assert criar_noticia(idioma=idioma).idioma == idioma


@pytest.mark.parametrize("idioma", ["PT", "es", "pt-BR", "", None])
def test_rejeita_idioma_invalido(idioma):
    with pytest.raises(ValueError):
        criar_noticia(idioma=idioma)


@pytest.mark.parametrize("link", [None, "", "   "])
def test_rejeita_noticia_sem_link(link):
    # O link é a identidade da notícia (usado na deduplicação).
    with pytest.raises(ValueError):
        criar_noticia(link=link)


def test_campos_so_por_nome():
    # Evita trocar titulo e link de lugar sem perceber.
    with pytest.raises(TypeError):
        Noticia("titulo", "https://exemplo.com", "Fonte", "pt", "primaria")

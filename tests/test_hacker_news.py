"""Testes da fonte Hacker News. Nenhum teste acessa a internet: a parte pura usa
a fixture fictícia, e a parte de rede usa uma sessão falsa que responde por URL."""

import json
import logging
from dataclasses import asdict
from pathlib import Path

import pytest

from core.modelo import NAO_INFORMADO
from fontes.base import Fonte
from fontes.hacker_news import (LIMITE_PADRAO, URL_API, HackerNews, converter_item,
                                link_da_discussao)

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "hn_ficticio.json")
                     .read_text(encoding="utf-8"))
ITENS = FIXTURE["itens"]


def item(id_):
    return ITENS[str(id_)]


# ------------------------------------------------------------ parte pura

def test_story_com_url():
    noticia = converter_item(item(101))

    assert noticia.titulo == "Show HN: Uma biblioteca Python fictícia"  # espaços juntados
    assert noticia.link == "https://exemplo.com/biblioteca?utm_source=hn"
    assert noticia.fonte == "Hacker News"
    assert noticia.data_publicacao == "2026-11-18T11:06:40+00:00"  # "time" é Unix
    assert noticia.resumo == NAO_INFORMADO
    assert noticia.tags == []
    assert noticia.idioma == "en"
    assert noticia.origem == "comunidade"


def test_nao_salva_o_autor():
    # CLAUDE.md: não salvar o campo "by".
    texto = json.dumps(asdict(converter_item(item(101))), ensure_ascii=False)

    assert "autor_ficticio_1" not in texto


def test_ask_hn_sem_url_usa_o_link_da_discussao_e_nao_salva_o_texto():
    noticia = converter_item(item(102))

    assert noticia.link == "https://news.ycombinator.com/item?id=102"
    # "text" é o post inteiro de quem escreveu, não um resumo publicado pela fonte.
    assert noticia.resumo == NAO_INFORMADO


def test_url_que_nao_e_web_cai_no_link_da_discussao():
    assert converter_item(item(106)).link == "https://news.ycombinator.com/item?id=106"


@pytest.mark.parametrize("id_", [103, 104, 105, 107])  # job, deleted, dead, poll
def test_itens_que_nao_sao_noticia_sao_ignorados(id_):
    assert converter_item(item(id_)) is None


@pytest.mark.parametrize("valor", [None, [], "texto", {}])
def test_resposta_vazia_ou_estranha_e_ignorada(valor):
    # A API devolve null para IDs que não existem.
    assert converter_item(valor) is None


def test_nome_idioma_e_origem_vem_dos_parametros():
    noticia = converter_item(item(101), fonte="HN", idioma="en", origem="comunidade")

    assert noticia.fonte == "HN"


def test_link_da_discussao():
    assert link_da_discussao(123) == "https://news.ycombinator.com/item?id=123"


# --------------------------------------------- rede (com sessão falsa)

class RespostaFalsa:
    def __init__(self, conteudo=b"", status=200):
        self.content = conteudo
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class SessaoFalsa:
    """Responde cada URL com o que está em `respostas` (bytes ou código de erro)."""

    def __init__(self, respostas):
        self.respostas = respostas
        self.chamadas = []

    def get(self, url, **kwargs):
        self.chamadas.append(url)
        resposta = self.respostas.get(url, 404)
        if isinstance(resposta, int):
            return RespostaFalsa(status=resposta)
        return RespostaFalsa(resposta)


def respostas_da_fixture(ids, lista="topstories"):
    respostas = {f"{URL_API}{lista}.json": json.dumps(ids).encode()}
    for id_, dados in ITENS.items():
        respostas[f"{URL_API}item/{id_}.json"] = json.dumps(dados).encode()
    return respostas


def criar_fonte(sessao, limite=LIMITE_PADRAO, lista="topstories", pausas=None):
    return HackerNews(nome="Hacker News", idioma="en", origem="comunidade",
                      lista=lista, limite=limite, sessao=sessao,
                      pausa=0.5, dormir=(pausas.append if pausas is not None else lambda s: None))


def test_coletar_busca_a_lista_e_depois_cada_item():
    sessao = SessaoFalsa(respostas_da_fixture([101, 102, 103, 104, 105, 106, 107]))

    noticias = criar_fonte(sessao).coletar()

    assert isinstance(criar_fonte(sessao), Fonte)
    assert [n.link for n in noticias] == [
        "https://exemplo.com/biblioteca?utm_source=hn",
        "https://news.ycombinator.com/item?id=102",
        "https://news.ycombinator.com/item?id=106",
    ]
    assert sessao.chamadas[0] == f"{URL_API}topstories.json"


def test_coletar_respeita_o_limite_de_itens():
    ids = list(range(1, 41))  # 40 IDs na lista
    sessao = SessaoFalsa({f"{URL_API}topstories.json": json.dumps(ids).encode()})

    criar_fonte(sessao, limite=30).coletar()

    itens_pedidos = [url for url in sessao.chamadas if "/item/" in url]
    assert len(itens_pedidos) == 30
    assert itens_pedidos[0] == f"{URL_API}item/1.json"


def test_limite_padrao_e_30():
    assert LIMITE_PADRAO == 30


def test_outra_lista_newstories():
    sessao = SessaoFalsa(respostas_da_fixture([101], lista="newstories"))

    noticias = criar_fonte(sessao, lista="newstories").coletar()

    assert sessao.chamadas[0] == f"{URL_API}newstories.json"
    assert len(noticias) == 1


def test_lista_invalida_e_recusada():
    with pytest.raises(ValueError):
        criar_fonte(SessaoFalsa({}), lista="../../outra-coisa")


def test_falha_de_um_item_nao_derruba_os_outros(caplog):
    respostas = respostas_da_fixture([101, 999, 102])
    respostas[f"{URL_API}item/999.json"] = 500
    sessao = SessaoFalsa(respostas)

    with caplog.at_level(logging.WARNING):
        noticias = criar_fonte(sessao).coletar()

    assert len(noticias) == 2
    assert "999" in caplog.text


def test_item_null_da_api_e_ignorado():
    respostas = respostas_da_fixture([101, 555])
    respostas[f"{URL_API}item/555.json"] = b"null"

    assert len(criar_fonte(SessaoFalsa(respostas)).coletar()) == 1


def test_falha_na_lista_sobe_para_o_main():
    sessao = SessaoFalsa({f"{URL_API}topstories.json": 429})

    with pytest.raises(RuntimeError):
        criar_fonte(sessao).coletar()
    assert len(sessao.chamadas) == 1  # não insiste


def test_lista_que_nao_e_lista_de_ids_gera_erro():
    sessao = SessaoFalsa({f"{URL_API}topstories.json": b'{"erro": "x"}'})

    with pytest.raises(ValueError):
        criar_fonte(sessao).coletar()


def test_pausa_entre_os_itens_mas_nao_antes_do_primeiro():
    pausas = []
    sessao = SessaoFalsa(respostas_da_fixture([101, 102, 103]))

    criar_fonte(sessao, pausas=pausas).coletar()

    assert pausas == [0.5, 0.5]

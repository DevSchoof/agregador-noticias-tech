"""Testes da fonte RSS/Atom genérica. Nenhum teste acessa a internet:
a parte pura usa as fixtures fictícias, e a parte de rede usa uma sessão falsa."""

import logging
from pathlib import Path

import pytest

from fontes.base import TIMEOUT_PADRAO, USER_AGENT, Fonte
from fontes.rss_generico import RssGenerico, buscar_feed, converter_feed
from core.modelo import NAO_INFORMADO

FIXTURES = Path(__file__).parent / "fixtures"


def ler_fixture(nome):
    return (FIXTURES / nome).read_bytes()


def converter_rss():
    return converter_feed(ler_fixture("rss_ficticio.xml"), fonte="Blog Fictício",
                          idioma="pt", origem="primaria")


def converter_atom():
    return converter_feed(ler_fixture("atom_ficticio.xml"), fonte="Releases Fictícias",
                          idioma="en", origem="primaria")


def por_link(noticias, trecho):
    return next(n for n in noticias if trecho in n.link)


# ------------------------------------------------------------ RSS 2.0

def test_rss_item_completo():
    noticia = por_link(converter_rss(), "python-9-9")

    assert noticia.titulo == "Python 9.9 fictício lançado"
    assert noticia.link == "https://exemplo.com/posts/python-9-9?utm_source=rss"
    assert noticia.fonte == "Blog Fictício"
    assert noticia.data_publicacao == "2026-11-16T13:30:00+00:00"  # -03:00 vira UTC
    assert noticia.resumo == "Uma versão imaginária com novidades & correções."
    assert noticia.tags == ["Python", "Lançamentos"]
    assert noticia.idioma == "pt"
    assert noticia.origem == "primaria"
    assert noticia.area == "tech"


def test_rss_titulo_texto_puro_nao_perde_simbolos():
    # "<int>" no título não é tag HTML: não pode sumir.
    noticia = por_link(converter_rss(), "list-int")

    assert noticia.titulo == "Como usar List<int> & dicionários"


def test_rss_sem_data_vira_nao_informado():
    assert por_link(converter_rss(), "list-int").data_publicacao == NAO_INFORMADO


def test_rss_sem_categorias_tem_tags_vazias():
    assert por_link(converter_rss(), "list-int").tags == []


def test_rss_so_com_conteudo_completo_nao_salva_resumo():
    # Regra de direitos autorais: o feedparser copia o content:encoded para o
    # summary quando não há description; isso NÃO é um resumo da fonte.
    noticia = por_link(converter_rss(), "posts/conteudo")

    assert noticia.resumo == NAO_INFORMADO
    assert "texto completo" not in noticia.resumo


def test_rss_item_sem_link_e_descartado_e_registrado(caplog):
    with caplog.at_level(logging.WARNING):
        noticias = converter_rss()

    assert len(noticias) == 4
    assert all(n.titulo != "Item quebrado sem link" for n in noticias)
    assert "sem link" in caplog.text.lower()


def test_rss_link_que_nao_e_web_e_descartado_e_registrado(caplog):
    feed = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>
      <item><title>Malicioso</title><link>javascript:alert(1)</link></item>
      <item><title>Dados embutidos</title><link>data:text/html,oi</link></item>
      <item><title>Normal</title><link>https://exemplo.com/normal</link></item>
    </channel></rss>"""

    with caplog.at_level(logging.WARNING):
        noticias = converter_feed(feed, fonte="F", idioma="pt", origem="primaria")

    assert [n.titulo for n in noticias] == ["Normal"]
    assert caplog.text.count("descartado") == 2


def test_rss_sem_titulo_data_invalida_e_resumo_longo():
    noticia = por_link(converter_rss(), "sem-titulo")

    assert noticia.titulo == NAO_INFORMADO
    assert noticia.data_publicacao == NAO_INFORMADO
    assert len(noticia.resumo) <= 300
    assert noticia.resumo.endswith("…")


def test_rss_mantem_a_ordem_do_feed():
    links = [n.link for n in converter_rss()]

    assert links == [
        "https://exemplo.com/posts/python-9-9?utm_source=rss",
        "https://exemplo.com/posts/list-int",
        "https://exemplo.com/posts/conteudo",
        "https://exemplo.com/posts/sem-titulo",
    ]


# --------------------------------------------------------------- Atom

def test_atom_release_so_com_updated_e_content():
    noticia = por_link(converter_atom(), "8.3.4")

    assert noticia.titulo == "8.3.4"
    assert noticia.link == "https://exemplo.com/projeto-ficticio/releases/tag/8.3.4"
    assert noticia.data_publicacao == "2026-11-20T15:00:00+00:00"
    assert noticia.resumo == NAO_INFORMADO  # <content> são as notas completas
    assert noticia.idioma == "en"


def test_atom_prefere_published_e_usa_summary_proprio():
    noticia = por_link(converter_atom(), "8.3.3")

    assert noticia.titulo == "8.3.3 estável"  # título marcado como HTML: tags saem
    assert noticia.data_publicacao == "2026-11-10T07:00:00+00:00"
    assert noticia.resumo == "Versão de manutenção fictícia."
    assert noticia.tags == ["release"]


# ------------------------------------------------------ casos de borda

def test_feed_vazio_devolve_lista_vazia():
    vazio = b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>'

    assert converter_feed(vazio, fonte="F", idioma="pt", origem="primaria") == []


def test_conteudo_que_nao_e_feed_gera_erro():
    # Erro claro para o main registrar no log (em vez de "0 notícias" em silêncio).
    with pytest.raises(ValueError):
        converter_feed(b"<html><body>Pagina de erro</body></html>",
                       fonte="F", idioma="pt", origem="primaria")


def test_texto_parecido_com_url_nao_e_baixado():
    # feedparser.parse("https://...") baixaria a URL; aqui tem que ser só texto.
    with pytest.raises(ValueError):
        converter_feed(b"https://exemplo.com/feed.xml",
                       fonte="F", idioma="pt", origem="primaria")


def test_origem_invalida_e_recusada():
    with pytest.raises(ValueError):
        converter_feed(ler_fixture("rss_ficticio.xml"), fonte="F",
                       idioma="pt", origem="oficial")


# --------------------------------------------- rede (com sessão falsa)

class RespostaFalsa:
    def __init__(self, conteudo=b"", status=200):
        self.content = conteudo
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class SessaoFalsa:
    """Imita requests.Session.get e guarda as chamadas recebidas."""

    def __init__(self, resposta):
        self.resposta = resposta
        self.chamadas = []

    def get(self, url, **kwargs):
        self.chamadas.append((url, kwargs))
        return self.resposta


def test_buscar_feed_envia_user_agent_e_timeout():
    sessao = SessaoFalsa(RespostaFalsa(b"<rss/>"))

    conteudo = buscar_feed("https://exemplo.com/feed.xml", sessao=sessao)

    assert conteudo == b"<rss/>"
    url, kwargs = sessao.chamadas[0]
    assert url == "https://exemplo.com/feed.xml"
    assert kwargs["headers"]["User-Agent"] == USER_AGENT
    assert kwargs["timeout"] == TIMEOUT_PADRAO


def test_buscar_feed_erro_http_sobe_sem_tentar_de_novo():
    # Ex.: 429 (muitas requisições). Uma chamada só, e o erro chega ao main.
    sessao = SessaoFalsa(RespostaFalsa(status=429))

    with pytest.raises(RuntimeError):
        buscar_feed("https://exemplo.com/feed.xml", sessao=sessao)
    assert len(sessao.chamadas) == 1


def test_user_agent_identifica_o_projeto_sem_email():
    assert "agregador-noticias" in USER_AGENT
    assert "@" not in USER_AGENT


def test_rss_generico_e_uma_fonte_e_coleta():
    sessao = SessaoFalsa(RespostaFalsa(ler_fixture("atom_ficticio.xml")))
    fonte = RssGenerico(nome="Releases Fictícias", url="https://exemplo.com/releases.atom",
                        idioma="en", origem="primaria", sessao=sessao)

    noticias = fonte.coletar()

    assert isinstance(fonte, Fonte)
    assert fonte.nome == "Releases Fictícias"
    assert [n.titulo for n in noticias] == ["8.3.4", "8.3.3 estável"]
    assert all(n.fonte == "Releases Fictícias" for n in noticias)
    assert sessao.chamadas[0][0] == "https://exemplo.com/releases.atom"


def test_fonte_base_nao_pode_ser_usada_direto():
    with pytest.raises(TypeError):
        Fonte(nome="x")

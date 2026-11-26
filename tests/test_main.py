"""Testes da orquestração (main.executar) com fontes FALSAS: nada acessa a internet.

A fábrica de fontes é trocada por uma que devolve fontes de teste, e a pausa
entre fontes é desligada para os testes rodarem rápido.
"""

import json
import logging

import pytest

from config.fontes import FONTES
from core.exportador import carregar_json
from core.modelo import Noticia
from fontes.base import Fonte
from fontes.rss_generico import RssGenerico
from main import criar_fonte, executar

TEMAS = {"pt": {"python": ["python"]}, "en": {"python": ["python"]}}


def noticia(titulo, link, fonte="Fonte Fictícia", origem="primaria",
            data="2026-11-16T10:00:00+00:00"):
    return Noticia(titulo=titulo, link=link, fonte=fonte, data_publicacao=data,
                   idioma="pt", origem=origem)


class FonteFalsa(Fonte):
    def __init__(self, nome, noticias=None, erro=None):
        super().__init__(nome)
        self.noticias = noticias or []
        self.erro = erro

    def coletar(self):
        if self.erro:
            raise self.erro
        return list(self.noticias)


def config(nome, filtrar=False, descartar_pre_versoes=False):
    return {"tipo": "falsa", "nome": nome, "url": "https://exemplo.com/feed",
            "idioma": "pt", "origem": "primaria", "filtrar": filtrar,
            "descartar_pre_versoes": descartar_pre_versoes}


def rodar(tmp_path, configs, fontes_falsas):
    """Executa o main com as fontes falsas indicadas por nome."""
    return executar(configs, pasta_dados=tmp_path, temas=TEMAS,
                    fabrica=lambda cfg: fontes_falsas[cfg["nome"]], pausa=0)


# ------------------------------------------------------------- fluxo

def test_salva_json_e_csv_com_as_noticias_coletadas(tmp_path):
    fontes = {"A": FonteFalsa("A", [noticia("Python A", "https://exemplo.com/a")])}

    rodar(tmp_path, [config("A")], fontes)

    assert [n.link for n in carregar_json(tmp_path / "noticias.json")] == ["https://exemplo.com/a"]
    assert (tmp_path / "noticias.csv").exists()


def test_falha_de_uma_fonte_nao_derruba_as_outras(tmp_path, caplog):
    fontes = {
        "Quebrada": FonteFalsa("Quebrada", erro=RuntimeError("HTTP 429")),
        "Boa": FonteFalsa("Boa", [noticia("Python B", "https://exemplo.com/b")]),
    }

    with caplog.at_level(logging.ERROR):
        resumo = rodar(tmp_path, [config("Quebrada"), config("Boa")], fontes)

    assert [n.link for n in carregar_json(tmp_path / "noticias.json")] == ["https://exemplo.com/b"]
    assert "Quebrada" in caplog.text and "HTTP 429" in caplog.text
    assert resumo["falhas"] == ["Quebrada"]


def test_erro_ao_criar_a_fonte_tambem_nao_derruba(tmp_path):
    def fabrica(cfg):
        if cfg["nome"] == "Tipo errado":
            raise ValueError("tipo desconhecido")
        return FonteFalsa(cfg["nome"], [noticia("Python C", "https://exemplo.com/c")])

    resumo = executar([config("Tipo errado"), config("Boa")], pasta_dados=tmp_path,
                      temas=TEMAS, fabrica=fabrica, pausa=0)

    assert resumo["falhas"] == ["Tipo errado"]
    assert len(carregar_json(tmp_path / "noticias.json")) == 1


def test_filtro_so_nas_fontes_com_filtrar_true(tmp_path):
    fontes = {
        "Geral": FonteFalsa("Geral", [
            noticia("Novidades do Python", "https://exemplo.com/g1"),
            noticia("Preço do café sobe", "https://exemplo.com/g2"),
        ]),
        "Do tema": FonteFalsa("Do tema", [noticia("8.3.4", "https://exemplo.com/t1")]),
    }

    rodar(tmp_path, [config("Geral", filtrar=True), config("Do tema", filtrar=False)], fontes)

    links = sorted(n.link for n in carregar_json(tmp_path / "noticias.json"))
    assert links == ["https://exemplo.com/g1", "https://exemplo.com/t1"]


def test_descarta_pre_versoes_so_nas_fontes_que_pedem(tmp_path):
    releases = [noticia("Nightly", "https://exemplo.com/r/nightly"),
                noticia("10.0.0.dev0", "https://exemplo.com/r/dev"),
                noticia("9.2.0", "https://exemplo.com/r/9.2.0")]
    fontes = {
        "Releases": FonteFalsa("Releases", releases),
        "Blog": FonteFalsa("Blog", [noticia("Python 3.16.0 alpha 2 is now available",
                                            "https://exemplo.com/blog/alpha")]),
    }

    resumo = rodar(tmp_path, [config("Releases", descartar_pre_versoes=True),
                              config("Blog")], fontes)

    links = sorted(n.link for n in carregar_json(tmp_path / "noticias.json"))
    # O post do blog sobre a alpha continua: a opção vale só para "Releases".
    assert links == ["https://exemplo.com/blog/alpha", "https://exemplo.com/r/9.2.0"]
    assert resumo["coletadas"] == 4 and resumo["depois_do_filtro"] == 2


def test_resumo_da_execucao(tmp_path):
    tmp_path.joinpath("noticias.json").write_text("[]", encoding="utf-8")
    fontes = {"A": FonteFalsa("A", [
        noticia("Python 1", "https://exemplo.com/1"),
        noticia("Café", "https://exemplo.com/2"),
    ])}

    resumo = rodar(tmp_path, [config("A", filtrar=True)], fontes)

    assert resumo == {"coletadas": 2, "depois_do_filtro": 1, "repetidas": 0,
                      "total_salvo": 1, "falhas": []}


# ---------------------------------------------------------- acumular

def test_duas_execucoes_acumulam_sem_repetir(tmp_path):
    primeira = {"A": FonteFalsa("A", [noticia("Python 1", "https://exemplo.com/1")])}
    segunda = {"A": FonteFalsa("A", [
        noticia("Python 1", "https://exemplo.com/1?utm_source=rss"),  # repetida
        noticia("Python 2", "https://exemplo.com/2"),
    ])}

    rodar(tmp_path, [config("A")], primeira)
    resumo = rodar(tmp_path, [config("A")], segunda)

    links = sorted(n.link for n in carregar_json(tmp_path / "noticias.json"))
    assert links == ["https://exemplo.com/1", "https://exemplo.com/2"]
    assert resumo["repetidas"] == 1 and resumo["total_salvo"] == 2


def test_todas_as_fontes_falham_mantem_o_historico(tmp_path):
    antes = {"A": FonteFalsa("A", [noticia("Python 1", "https://exemplo.com/1")])}
    rodar(tmp_path, [config("A")], antes)

    quebrada = {"A": FonteFalsa("A", erro=RuntimeError("fora do ar"))}
    rodar(tmp_path, [config("A")], quebrada)

    assert len(carregar_json(tmp_path / "noticias.json")) == 1


def test_json_corrompido_para_a_execucao_sem_sobrescrever(tmp_path):
    caminho = tmp_path / "noticias.json"
    caminho.write_text("[{ isto não é json", encoding="utf-8")
    fontes = {"A": FonteFalsa("A", [noticia("Python 1", "https://exemplo.com/1")])}

    with pytest.raises(json.JSONDecodeError):
        rodar(tmp_path, [config("A")], fontes)

    assert caminho.read_text(encoding="utf-8") == "[{ isto não é json"


def test_pausa_entre_fontes_mas_nao_depois_da_ultima(tmp_path, monkeypatch):
    pausas = []
    monkeypatch.setattr("main.time.sleep", pausas.append)
    fontes = {n: FonteFalsa(n) for n in ("A", "B", "C")}

    executar([config("A"), config("B"), config("C")], pasta_dados=tmp_path,
             temas=TEMAS, fabrica=lambda cfg: fontes[cfg["nome"]], pausa=2)

    assert pausas == [2, 2]


# ------------------------------------------------------ fábrica/config

def test_criar_fonte_rss():
    fonte = criar_fonte({"tipo": "rss", "nome": "X", "url": "https://exemplo.com/feed.xml",
                         "idioma": "en", "origem": "primaria", "filtrar": False})

    assert isinstance(fonte, RssGenerico)
    assert (fonte.nome, fonte.url, fonte.idioma, fonte.origem) == (
        "X", "https://exemplo.com/feed.xml", "en", "primaria")


def test_criar_fonte_tipo_desconhecido():
    with pytest.raises(ValueError):
        criar_fonte({"tipo": "xyz", "nome": "X"})


def test_config_real_e_valida():
    nomes = [cfg["nome"] for cfg in FONTES]
    assert len(nomes) == len(set(nomes))  # nomes únicos (aparecem no log)
    for cfg in FONTES:
        assert cfg["idioma"] in ("pt", "en")
        assert cfg["origem"] in ("primaria", "comunidade")
        assert isinstance(cfg["filtrar"], bool)
        assert isinstance(cfg.get("descartar_pre_versoes", False), bool)
        assert cfg["url"].startswith("https://")
        assert isinstance(criar_fonte(cfg), Fonte)  # só cria, não coleta

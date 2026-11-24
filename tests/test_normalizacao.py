"""Testes das funções de normalização (texto, resumo, link e data). Dados fictícios."""

import time
from datetime import datetime, timedelta, timezone

import pytest

from core.modelo import NAO_INFORMADO
from core.normalizacao import (
    cortar_resumo,
    limpar_html,
    normalizar_data,
    normalizar_link,
    normalizar_texto,
    remover_acentos,
)


# ---------------------------------------------------------------- limpar_html

def test_limpar_html_remove_tags():
    assert limpar_html("<p>Olá <b>mundo</b></p>") == "Olá mundo"


def test_limpar_html_converte_entidades():
    assert limpar_html("Python &amp; dados") == "Python & dados"


def test_limpar_html_entidade_de_tag_vira_texto_e_nao_e_removida():
    assert limpar_html("use &lt;div&gt; no layout") == "use <div> no layout"


def test_limpar_html_separa_palavras_de_blocos_diferentes():
    assert limpar_html("<p>um</p><p>dois</p>") == "um dois"
    assert limpar_html("linha<br>outra") == "linha outra"


def test_limpar_html_nao_cria_espaco_antes_de_pontuacao_em_tag_inline():
    assert limpar_html('veja <a href="https://exemplo.com">aqui</a>.') == "veja aqui."


def test_limpar_html_descarta_script_e_style():
    texto = "<style>p {color: red}</style>Texto<script>alert(1)</script> visível"
    assert limpar_html(texto) == "Texto visível"


def test_limpar_html_junta_espacos_e_quebras_de_linha():
    assert limpar_html("  muito\n\n   espaço\t aqui  ") == "muito espaço aqui"


def test_limpar_html_texto_sem_html_fica_igual():
    assert limpar_html("Texto simples.") == "Texto simples."


def test_limpar_html_none_vira_texto_vazio():
    assert limpar_html(None) == ""


# -------------------------------------------------------------- cortar_resumo

def test_cortar_resumo_texto_curto_fica_igual():
    assert cortar_resumo("Resumo curto.") == "Resumo curto."


def test_cortar_resumo_texto_no_limite_fica_igual():
    texto = "a" * 300
    assert cortar_resumo(texto) == texto


def test_cortar_resumo_texto_longo_respeita_limite_e_termina_com_reticencias():
    texto = "palavra " * 100  # 800 caracteres
    resumo = cortar_resumo(texto)

    assert len(resumo) <= 300
    assert resumo.endswith("…")


def test_cortar_resumo_nao_corta_palavra_no_meio():
    texto = "palavra " * 100
    resumo = cortar_resumo(texto)

    assert resumo.endswith("palavra…")


def test_cortar_resumo_sem_espacos_corta_no_limite():
    resumo = cortar_resumo("a" * 400)

    assert len(resumo) == 300
    assert resumo.endswith("…")


def test_cortar_resumo_aceita_outro_limite():
    resumo = cortar_resumo("um dois tres quatro", limite=10)

    assert resumo == "um dois…"


def test_cortar_resumo_none_vira_texto_vazio():
    assert cortar_resumo(None) == ""


# ------------------------------------------------------------ normalizar_link

def test_normalizar_link_remove_parametros_utm_e_mantem_os_outros():
    link = "https://exemplo.com/a?id=5&utm_source=feed&utm_medium=rss"
    assert normalizar_link(link) == "https://exemplo.com/a?id=5"


def test_normalizar_link_sem_parametros_restantes_nao_deixa_interrogacao():
    assert normalizar_link("https://exemplo.com/a?utm_source=feed") == "https://exemplo.com/a"


@pytest.mark.parametrize("parametro", ["fbclid", "gclid", "UTM_Campaign"])
def test_normalizar_link_remove_outros_parametros_de_rastreio(parametro):
    link = f"https://exemplo.com/a?{parametro}=abc123"
    assert normalizar_link(link) == "https://exemplo.com/a"


def test_normalizar_link_mantem_ordem_dos_parametros():
    link = "https://exemplo.com/busca?q=python&pagina=2"
    assert normalizar_link(link) == "https://exemplo.com/busca?q=python&pagina=2"


def test_normalizar_link_remove_fragmento():
    assert normalizar_link("https://exemplo.com/a#comentarios") == "https://exemplo.com/a"


def test_normalizar_link_remove_barra_final():
    assert normalizar_link("https://exemplo.com/a/") == "https://exemplo.com/a"
    assert normalizar_link("https://exemplo.com/") == "https://exemplo.com"


def test_normalizar_link_dominio_em_minusculas_e_caminho_preservado():
    link = "HTTPS://Exemplo.COM/Caminho/Artigo"
    assert normalizar_link(link) == "https://exemplo.com/Caminho/Artigo"


def test_normalizar_link_remove_espacos_nas_pontas():
    assert normalizar_link("  https://exemplo.com/a \n") == "https://exemplo.com/a"


def test_normalizar_link_variantes_do_mesmo_link_ficam_iguais():
    variantes = [
        "https://exemplo.com/noticia",
        "https://EXEMPLO.com/noticia/",
        "https://exemplo.com/noticia?utm_source=x#topo",
    ]
    assert {normalizar_link(v) for v in variantes} == {"https://exemplo.com/noticia"}


def test_normalizar_link_mantem_link_de_discussao_do_hacker_news():
    link = "https://news.ycombinator.com/item?id=123"
    assert normalizar_link(link) == link


# ------------------------------------------------------------ normalizar_data

ESPERADO = "2026-11-16T10:00:00+00:00"


def test_normalizar_data_iso_com_z():
    assert normalizar_data("2026-11-16T10:00:00Z") == ESPERADO


def test_normalizar_data_iso_com_outro_fuso_converte_para_utc():
    assert normalizar_data("2026-11-16T07:00:00-03:00") == ESPERADO


def test_normalizar_data_formato_rss():
    assert normalizar_data("Mon, 16 Nov 2026 10:00:00 GMT") == ESPERADO
    assert normalizar_data("Mon, 16 Nov 2026 07:00:00 -0300") == ESPERADO


def test_normalizar_data_struct_time_do_feedparser():
    # O feedparser entrega as datas já em UTC neste formato.
    data = time.struct_time((2026, 11, 16, 10, 0, 0, 0, 320, 0))
    assert normalizar_data(data) == ESPERADO


def test_normalizar_data_timestamp_unix_do_hacker_news():
    timestamp = int(datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc).timestamp())
    assert normalizar_data(timestamp) == ESPERADO


def test_normalizar_data_datetime_sem_fuso_e_tratado_como_utc():
    assert normalizar_data(datetime(2026, 11, 16, 10, 0)) == ESPERADO


def test_normalizar_data_datetime_com_fuso_converte_para_utc():
    fuso_brasilia = timezone(timedelta(hours=-3))
    assert normalizar_data(datetime(2026, 11, 16, 7, 0, tzinfo=fuso_brasilia)) == ESPERADO


def test_normalizar_data_descarta_microssegundos():
    assert normalizar_data("2026-11-16T10:00:00.123456+00:00") == ESPERADO


@pytest.mark.parametrize("valor", [None, "", "   ", "ontem", NAO_INFORMADO])
def test_normalizar_data_ausente_ou_invalida_vira_nao_informado(valor):
    assert normalizar_data(valor) == NAO_INFORMADO


# ---------------------------------------------------- remover_acentos e texto

def test_remover_acentos():
    assert remover_acentos("Ação é ótima, Çedilha") == "Acao e otima, Cedilha"


def test_normalizar_texto_sem_acento_sem_caixa_sem_pontuacao():
    assert normalizar_texto("Automação: IA & Dados!") == "automacao ia dados"


def test_normalizar_texto_hifen_separa_palavras():
    assert normalizar_texto("Machine-Learning") == "machine learning"


def test_normalizar_texto_junta_espacos():
    assert normalizar_texto("  Python   em\tprodução ") == "python em producao"


def test_normalizar_texto_none_vira_texto_vazio():
    assert normalizar_texto(None) == ""

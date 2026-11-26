"""Fixtures dos testes E2E: servidor da página, navegadores e evidências na falha.

Rodar:  pytest -m e2e
Escolher navegadores:  E2E_NAVEGADORES=chrome   (padrão: chrome,firefox)
Firefox fora do lugar padrão:  FIREFOX_BINARY=C:\\caminho\\firefox.exe

A página roda neste computador (127.0.0.1) e lê um JSON FICTÍCIO: os testes não
dependem da internet. Observação: na primeira execução, o Selenium Manager
baixa o driver do navegador (chromedriver/geckodriver) e guarda em cache.
"""

import os
import threading
from pathlib import Path

import pytest
from selenium import webdriver
from werkzeug.serving import make_server

from core.exportador import salvar_json
from core.modelo import Noticia
from tests.e2e.evidencias import salvar_evidencias
from web.app import criar_app

PASTA_EVIDENCIAS = Path(__file__).resolve().parents[2] / "evidencias_e2e"
NAVEGADORES = [n.strip() for n in os.environ.get("E2E_NAVEGADORES", "chrome,firefox").split(",")
               if n.strip()]


# ------------------------------------------------------------- dados

def noticias_ficticias():
    """Conjunto fixo e fictício usado por todos os testes E2E."""
    def n(titulo, numero, **outros):
        campos = dict(fonte="Blog Fictício", idioma="en", origem="primaria",
                      data_publicacao=f"2026-11-{20 - numero:02d}T10:00:00+00:00")
        campos.update(outros)
        return Noticia(titulo=titulo, link=f"https://exemplo.com/{numero}", **campos)

    return [
        n("Python 9.9 fictício lançado", 1, resumo="Uma versão imaginária."),
        n("Selenium 9.0 fictício", 2, fonte="Releases Fictícias"),
        n("Novo modelo de AI fictício", 3, fonte="Fórum Fictício", origem="comunidade"),
        n("Automação com Python no Brasil", 4, fonte="Portal Fictício", idioma="pt",
          origem="comunidade"),
    ]


# ----------------------------------------------------------- servidor

@pytest.fixture(scope="session")
def servidor(tmp_path_factory):
    """Sobe a página numa thread, numa porta livre, e devolve o endereço base.

    Porta 0 = o sistema escolhe uma livre (nunca briga com outro servidor).
    """
    caminho = tmp_path_factory.mktemp("dados_e2e") / "noticias.json"
    salvar_json(noticias_ficticias(), caminho)

    servidor_http = make_server("127.0.0.1", 0, criar_app(caminho), threaded=True)
    thread = threading.Thread(target=servidor_http.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{servidor_http.server_port}"
    servidor_http.shutdown()
    thread.join(timeout=5)


# --------------------------------------------------------- navegadores

def _abrir_chrome():
    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1280,900")
    opcoes.add_argument("--no-sandbox")  # necessário em contêineres de CI
    return webdriver.Chrome(options=opcoes)


def _abrir_firefox():
    opcoes = webdriver.FirefoxOptions()
    opcoes.add_argument("-headless")
    opcoes.add_argument("--width=1280")
    opcoes.add_argument("--height=900")
    if os.environ.get("FIREFOX_BINARY"):
        opcoes.binary_location = os.environ["FIREFOX_BINARY"]
    return webdriver.Firefox(options=opcoes)


ABRIR = {"chrome": _abrir_chrome, "firefox": _abrir_firefox}


@pytest.fixture(scope="session", params=NAVEGADORES)
def navegador(request):
    """Um navegador por sessão de testes (abrir um por teste seria lento).

    Cada teste roda uma vez em cada navegador da lista.
    """
    nome = request.param
    if nome not in ABRIR:
        raise ValueError(f"Navegador desconhecido em E2E_NAVEGADORES: {nome!r}")
    driver = ABRIR[nome]()
    driver.set_page_load_timeout(15)
    yield driver
    driver.quit()


# ------------------------------------------------- evidência na falha

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Guarda no teste o resultado de cada fase (preparação, execução, final),
    para a fixture abaixo saber se o teste falhou."""
    resultado = yield
    relatorio = resultado.get_result()
    setattr(item, f"relatorio_{relatorio.when}", relatorio)


@pytest.fixture(autouse=True)
def evidencia_na_falha(request):
    """Depois de cada teste E2E: se ele falhou, salva print e HTML."""
    yield
    relatorio = getattr(request.node, "relatorio_call", None)
    if relatorio is not None and relatorio.failed and "navegador" in request.fixturenames:
        driver = request.getfixturevalue("navegador")
        salvar_evidencias(driver, PASTA_EVIDENCIAS, request.node.name)

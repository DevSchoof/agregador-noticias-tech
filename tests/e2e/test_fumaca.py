"""Teste de fumaça (smoke test): prova que a estrutura E2E funciona.

Sobe o servidor, abre o navegador headless e confere o básico da página.
Os testes de verdade (com Page Object) vêm na próxima sprint.
"""

import pytest
from selenium.webdriver.common.by import By

pytestmark = pytest.mark.e2e  # todos os testes deste arquivo são E2E


def test_pagina_abre_com_titulo_e_noticias(navegador, servidor):
    navegador.get(servidor)

    assert navegador.title == "Notícias de tecnologia"
    assert navegador.find_element(By.TAG_NAME, "h1").text == "Notícias de tecnologia"
    assert len(navegador.find_elements(By.CSS_SELECTOR, '[data-testid="noticia"]')) == 4

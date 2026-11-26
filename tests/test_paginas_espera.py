"""Testes da espera pela troca de página do Page Object (sem navegador).

Bug encontrado no GitHub Actions (2026-11-26, Chrome 157): no meio da troca de
página, o Chrome respondeu "Node with given id does not belong to the document"
em vez de dizer que o elemento antigo sumiu, e o teste E2E caiu, embora a página
tivesse carregado certo. Este arquivo reproduz isso com um elemento falso.
"""

import pytest
from selenium.common.exceptions import (StaleElementReferenceException, TimeoutException,
                                        WebDriverException)

from tests.e2e.paginas import esperar_troca_de_pagina

ERRO_NO_MEIO_DA_TROCA = WebDriverException(
    'unknown error: unhandled inspector error: {"code":-32000,'
    '"message":"Node with given id does not belong to the document"}')


class ElementoFalso:
    """Imita o <html> da página antiga. Cada chamada a is_enabled() consome o
    próximo item da lista: True = ainda existe; uma exceção = é levantada."""

    def __init__(self, respostas):
        self.respostas = list(respostas)

    def is_enabled(self):
        resposta = self.respostas.pop(0) if self.respostas else True
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


NAVEGADOR_FALSO = object()  # a espera não usa o navegador, só o elemento


def esperar(elemento, tempo=1.0):
    return esperar_troca_de_pagina(NAVEGADOR_FALSO, elemento, tempo=tempo, intervalo=0.01)


def test_conclui_quando_o_elemento_antigo_some():
    elemento = ElementoFalso([True, True, StaleElementReferenceException()])

    assert esperar(elemento) is True


def test_erro_no_meio_da_troca_nao_derruba_a_espera():
    # O bug: esse erro do Chrome deve ser tratado como "ainda trocando".
    elemento = ElementoFalso([True, ERRO_NO_MEIO_DA_TROCA, StaleElementReferenceException()])

    assert esperar(elemento) is True


def test_pagina_que_nunca_troca_continua_falhando_por_tempo():
    # A correção não pode esconder um defeito real: sem troca, o teste falha.
    elemento = ElementoFalso([])  # sempre "ainda existe"

    with pytest.raises(TimeoutException):
        esperar(elemento, tempo=0.1)

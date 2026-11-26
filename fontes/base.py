"""Interface comum das fontes: toda fonte sabe coletar() e devolver list[Noticia].

O main não precisa saber se a fonte é RSS, Atom ou API: só chama coletar().
"""

from abc import ABC, abstractmethod

import requests

from core.modelo import Noticia

# Identifica o projeto para quem recebe a requisição (sem e-mail, ver CLAUDE.md).
USER_AGENT = "agregador-noticias-portfolio/0.1 (projeto de estudo)"
TIMEOUT_PADRAO = 15  # segundos: sem timeout, uma fonte travada travaria a execução


def baixar(url, sessao=None, timeout=TIMEOUT_PADRAO):
    """Faz uma requisição GET educada e devolve os bytes da resposta.

    Usado por todas as fontes: sempre com User-Agent do projeto e timeout.
    Erro HTTP (404, 429...) sobe como exceção, sem nova tentativa: insistir
    sobrecarregaria a fonte. Quem chama decide o que fazer com o erro.
    """
    sessao = sessao or requests
    resposta = sessao.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resposta.raise_for_status()
    return resposta.content


class Fonte(ABC):
    """Classe base abstrata: não pode ser criada direto, só as subclasses."""

    def __init__(self, nome):
        self.nome = nome

    @abstractmethod
    def coletar(self) -> list[Noticia]:
        """Busca os dados na fonte e devolve as notícias já no formato do contrato."""

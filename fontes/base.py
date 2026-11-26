"""Interface comum das fontes: toda fonte sabe coletar() e devolver list[Noticia].

O main não precisa saber se a fonte é RSS, Atom ou API: só chama coletar().
"""

from abc import ABC, abstractmethod

from core.modelo import Noticia

# Identifica o projeto para quem recebe a requisição (sem e-mail, ver CLAUDE.md).
USER_AGENT = "agregador-noticias-portfolio/0.1 (projeto de estudo)"
TIMEOUT_PADRAO = 15  # segundos: sem timeout, uma fonte travada travaria a execução


class Fonte(ABC):
    """Classe base abstrata: não pode ser criada direto, só as subclasses."""

    def __init__(self, nome):
        self.nome = nome

    @abstractmethod
    def coletar(self) -> list[Noticia]:
        """Busca os dados na fonte e devolve as notícias já no formato do contrato."""

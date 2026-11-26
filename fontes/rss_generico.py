"""Fonte genérica para qualquer feed RSS ou Atom (Python Insider, releases do GitHub...).

Dividida em duas partes:
- buscar_feed: a parte de rede (requests). Testada com uma sessão falsa.
- converter_feed: a parte pura (bytes do feed -> list[Noticia]). Testada com fixtures.
"""

import io
import logging

import feedparser
import requests

from core.modelo import Noticia
from core.normalizacao import cortar_resumo, limpar_html, normalizar_data
from fontes.base import TIMEOUT_PADRAO, USER_AGENT, Fonte

logger = logging.getLogger(__name__)


# ------------------------------------------------------------ parte pura

def _titulo(entrada):
    """Título como texto. Só remove tags se o próprio feed diz que o título é HTML:
    em texto puro, "List<int>" tem que continuar "List<int>"."""
    titulo = entrada.get("title", "")
    tipo = entrada.get("title_detail", {}).get("type", "text/plain")
    if "html" in tipo:
        return limpar_html(titulo)
    return " ".join(titulo.split())


def _resumo(entrada):
    """Resumo curto, só se a fonte publicou um resumo de verdade.

    O feedparser copia o <content>/<content:encoded> (que pode ser o texto completo
    da matéria) para `summary` quando o item não tem resumo próprio. Nesse caso o
    "resumo" é igual ao conteúdo e é descartado (regra de direitos autorais).
    """
    resumo = entrada.get("summary", "")
    conteudos = [c.get("value", "") for c in entrada.get("content", [])]
    if not resumo or resumo in conteudos:
        return ""
    return cortar_resumo(limpar_html(resumo))


def _data(entrada):
    """Prefere a data de publicação; se não houver, a de atualização (Atom).

    dict.get direto: o .get do feedparser troca "updated" por "published" por conta
    própria (com aviso de que isso vai deixar de existir); aqui a escolha é explícita.
    """
    publicada = dict.get(entrada, "published_parsed")
    atualizada = dict.get(entrada, "updated_parsed")
    return normalizar_data(publicada or atualizada)


def _tags(entrada):
    return [t["term"].strip() for t in entrada.get("tags", []) if (t.get("term") or "").strip()]


def converter_feed(conteudo, *, fonte, idioma, origem):
    """Converte os bytes de um feed RSS/Atom em notícias, na ordem do feed.

    Itens sem link são descartados (com aviso no log) sem derrubar os outros.
    Conteúdo que não é feed gera ValueError, para o erro aparecer no log do main.
    """
    # BytesIO: o feedparser trata como conteúdo. Se recebesse uma string parecida
    # com URL, ele mesmo faria o download, e a parte pura não pode acessar a rede.
    resultado = feedparser.parse(io.BytesIO(conteudo))
    if not resultado.get("version"):
        motivo = resultado.get("bozo_exception", "formato não reconhecido")
        raise ValueError(f"{fonte}: o conteúdo não é um feed RSS/Atom ({motivo})")

    noticias = []
    for entrada in resultado.entries:
        link = (entrada.get("link") or "").strip()
        if not link:
            logger.warning("%s: item sem link descartado (título: %r)", fonte, entrada.get("title"))
            continue
        noticias.append(Noticia(
            titulo=_titulo(entrada),
            link=link,
            fonte=fonte,
            data_publicacao=_data(entrada),
            resumo=_resumo(entrada),
            tags=_tags(entrada),
            idioma=idioma,
            origem=origem,
        ))
    return noticias


# ----------------------------------------------------------- parte de rede

def buscar_feed(url, sessao=None, timeout=TIMEOUT_PADRAO):
    """Baixa o feed (uma requisição, sem repetir) e devolve os bytes.

    Erro HTTP (404, 429...) sobe como exceção: o main registra e segue com as
    outras fontes. Não insistir é de propósito, para não sobrecarregar a fonte.
    """
    sessao = sessao or requests
    resposta = sessao.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resposta.raise_for_status()
    return resposta.content


class RssGenerico(Fonte):
    """Uma fonte RSS/Atom configurada por nome, URL, idioma e origem."""

    def __init__(self, nome, url, idioma, origem, sessao=None):
        super().__init__(nome)
        self.url = url
        self.idioma = idioma
        self.origem = origem
        self.sessao = sessao  # None = requests de verdade; nos testes, uma sessão falsa

    def coletar(self):
        conteudo = buscar_feed(self.url, sessao=self.sessao)
        return converter_feed(conteudo, fonte=self.nome, idioma=self.idioma, origem=self.origem)

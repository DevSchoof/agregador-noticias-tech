"""Fonte Hacker News pela API oficial (https://github.com/HackerNews/API).

A API funciona em duas etapas:
1. <lista>.json (ex.: topstories.json) devolve só os IDs: [101, 102, ...].
2. item/<id>.json devolve cada item: título, url, data (Unix), tipo...

Dividida como as outras fontes:
- converter_item: a parte pura (dict da API -> Noticia ou None). Testada com fixture.
- HackerNews.coletar: a parte de rede (lista + um pedido por item).
"""

import json
import logging
import time

import requests

from core.modelo import Noticia, link_e_web
from core.normalizacao import normalizar_data
from fontes.base import Fonte, baixar

logger = logging.getLogger(__name__)

URL_API = "https://hacker-news.firebaseio.com/v0/"
URL_DISCUSSAO = "https://news.ycombinator.com/item?id={id}"
LISTAS_VALIDAS = ("topstories", "newstories", "beststories")
LIMITE_PADRAO = 30   # a API não tem limite, mas não precisamos de mais (CLAUDE.md)
PAUSA_PADRAO = 0.2   # segundos entre um item e o próximo, por educação


# ------------------------------------------------------------ parte pura

def link_da_discussao(id_item):
    return URL_DISCUSSAO.format(id=id_item)


def converter_item(item, *, fonte="Hacker News", idioma="en", origem="comunidade"):
    """Converte um item da API em Noticia. Devolve None se não for uma notícia.

    Ignorados: resposta vazia (a API devolve null), itens apagados ou removidos
    pela moderação (deleted/dead) e tipos que não são "story" (job, poll...).

    Regras do CLAUDE.md:
    - Sem "url" (Ask HN), o link é o da discussão no próprio Hacker News. Uma url
      que não é http/https também cai no link da discussão.
    - Não salva o autor ("by").
    - Não salva o "text": é o post inteiro de quem escreveu, não um resumo.
    """
    if not isinstance(item, dict) or not item:
        return None
    if item.get("deleted") or item.get("dead") or item.get("type") != "story":
        return None

    url = (item.get("url") or "").strip()
    link = url if link_e_web(url) else link_da_discussao(item.get("id"))

    return Noticia(
        titulo=" ".join((item.get("title") or "").split()),
        link=link,
        fonte=fonte,
        data_publicacao=normalizar_data(item.get("time")),
        idioma=idioma,
        origem=origem,
    )


# ----------------------------------------------------------- parte de rede

class HackerNews(Fonte):
    def __init__(self, nome="Hacker News", idioma="en", origem="comunidade",
                 lista="topstories", limite=LIMITE_PADRAO, sessao=None,
                 pausa=PAUSA_PADRAO, dormir=time.sleep):
        super().__init__(nome)
        # A lista entra na URL: só nomes conhecidos, nada vindo de fora.
        if lista not in LISTAS_VALIDAS:
            raise ValueError(f"lista inválida: {lista!r}. Use {LISTAS_VALIDAS}.")
        self.idioma = idioma
        self.origem = origem
        self.lista = lista
        self.limite = limite
        self.sessao = sessao
        self.pausa = pausa
        self.dormir = dormir  # time.sleep; nos testes, uma função que só anota

    def _buscar_json(self, sessao, caminho):
        return json.loads(baixar(URL_API + caminho, sessao=sessao))

    def coletar(self):
        # Uma Session reaproveita a conexão entre os ~30 pedidos (mais rápido e
        # mais leve para o servidor). Nos testes, vem a sessão falsa.
        sessao = self.sessao or requests.Session()

        # Falha aqui (lista) sobe para o main: sem a lista não há o que coletar.
        ids = self._buscar_json(sessao, f"{self.lista}.json")
        if not isinstance(ids, list):
            raise ValueError(f"{self.nome}: resposta de {self.lista} não é uma lista de IDs")

        noticias = []
        for posicao, id_item in enumerate(ids[: self.limite]):
            if posicao > 0 and self.pausa:
                self.dormir(self.pausa)
            # Falha num item só perde aquele item; os outros seguem.
            try:
                item = self._buscar_json(sessao, f"item/{int(id_item)}.json")
            except Exception as erro:
                logger.warning("%s: item %s ignorado (%s)", self.nome, id_item, erro)
                continue
            noticia = converter_item(item, fonte=self.nome, idioma=self.idioma,
                                     origem=self.origem)
            if noticia is not None:
                noticias.append(noticia)
        return noticias

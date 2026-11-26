"""Deduplicação em dois níveis e ordenação da saída.

Nível 1 (identidade): o mesmo link normalizado é a mesma notícia; só uma fica.
Nível 2 (suspeita): links diferentes com o mesmo título normalizado ficam as
duas, mas a que não é principal é marcada em `provavel_duplicata_de`.

A entrada deve vir com as notícias já salvas primeiro e as novas depois: em
caso de empate, ganha quem apareceu primeiro (a que já estava salva).
"""

from dataclasses import replace

from core.modelo import NAO_INFORMADO
from core.normalizacao import normalizar_link, normalizar_texto


def _sem_data(noticia):
    return noticia.data_publicacao == NAO_INFORMADO


def _remover_links_repetidos(noticias):
    """Nível 1: um representante por link normalizado. Primária ganha de comunidade;
    na mesma origem, fica a que apareceu primeiro."""
    escolhidas = {}  # link normalizado -> notícia (o dict mantém a ordem de chegada)
    for noticia in noticias:
        chave = normalizar_link(noticia.link)
        atual = escolhidas.get(chave)
        if atual is None:
            escolhidas[chave] = noticia
        elif atual.origem != "primaria" and noticia.origem == "primaria":
            escolhidas[chave] = noticia
    return list(escolhidas.values())


def _marcar_titulos_repetidos(noticias):
    """Nível 2: agrupa por título normalizado e marca todas menos a principal.

    Devolve cópias (dataclasses.replace): as notícias recebidas não são alteradas.
    A marca é recalculada do zero, então marcas antigas são apagadas primeiro.
    """
    noticias = [replace(n, provavel_duplicata_de="") for n in noticias]

    grupos = {}  # título normalizado -> posições na lista
    for posicao, noticia in enumerate(noticias):
        if noticia.titulo == NAO_INFORMADO:
            continue
        grupos.setdefault(normalizar_texto(noticia.titulo), []).append(posicao)

    for posicoes in grupos.values():
        if len(posicoes) < 2:
            continue
        # Principal: primária > comunidade; depois a publicada primeiro
        # (sem data por último); depois a que apareceu primeiro na lista.
        # Datas ISO em UTC no mesmo formato podem ser comparadas como texto.
        principal = min(posicoes, key=lambda p: (
            noticias[p].origem != "primaria",
            _sem_data(noticias[p]),
            noticias[p].data_publicacao,
            p,
        ))
        for posicao in posicoes:
            if posicao != principal:
                noticias[posicao].provavel_duplicata_de = noticias[principal].link
    return noticias


def _ordenar(noticias):
    """Primárias primeiro; dentro de cada grupo, da mais nova para a mais antiga;
    sem data no fim do grupo.

    Duas ordenações seguidas: o sort do Python é estável (empates mantêm a ordem
    anterior), então a segunda ordenação preserva a ordem por data da primeira.
    """
    por_data = sorted(
        noticias,
        key=lambda n: "" if _sem_data(n) else n.data_publicacao,
        reverse=True,  # "" (sem data) fica por último
    )
    return sorted(por_data, key=lambda n: n.origem != "primaria")


def deduplicar(noticias):
    """Remove links repetidos, marca títulos repetidos e ordena."""
    sem_links_repetidos = _remover_links_repetidos(noticias)
    marcadas = _marcar_titulos_repetidos(sem_links_repetidos)
    return _ordenar(marcadas)

"""Filtro por tema: decide se uma notícia fala de algum dos temas configurados.

Os temas chegam por parâmetro (o main passa config/temas.py), assim o núcleo
não depende da configuração e os testes usam temas próprios.
"""

from core.modelo import NAO_INFORMADO
from core.normalizacao import normalizar_texto


def _texto_da_noticia(noticia):
    """Junta título, resumo e tags num texto só, já normalizado."""
    partes = [noticia.titulo, noticia.resumo, *noticia.tags]
    partes = [p for p in partes if p and p != NAO_INFORMADO]
    return normalizar_texto(" ".join(partes))


def temas_da_noticia(noticia, temas):
    """Lista os temas encontrados na notícia, na ordem da config.

    `temas` é um dicionário {idioma: {tema: [palavras-chave]}}. Só as palavras
    do idioma da notícia são usadas.
    """
    # Espaços nas pontas: " python " só aparece dentro de " ... python ... "
    # se for palavra inteira. Funciona porque normalizar_texto já trocou a
    # pontuação por espaço e deixou um espaço só entre as palavras.
    texto = f" {_texto_da_noticia(noticia)} "

    encontrados = []
    for tema, palavras in temas.get(noticia.idioma, {}).items():
        if any(f" {normalizar_texto(p)} " in texto for p in palavras):
            encontrados.append(tema)
    return encontrados


def filtrar_por_tema(noticias, temas):
    """Devolve só as notícias com pelo menos um tema, na mesma ordem."""
    return [n for n in noticias if temas_da_noticia(n, temas)]

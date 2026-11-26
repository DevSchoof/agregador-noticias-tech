"""Lógica pura dos filtros da página: quais opções existem, quais valores pedidos
são válidos e quais notícias passam. Não depende do Flask (testável sozinha).

O tema não fica salvo na notícia: é calculado na hora com as palavras-chave de
config/temas.py (decisão do Eduardo em 2026-11-26).
"""

from core.filtro import temas_da_noticia

CAMPOS = ("origem", "fonte", "idioma", "tema")

ROTULOS = {
    "origem": {"primaria": "primária", "comunidade": "comunidade"},
    "idioma": {"pt": "português", "en": "inglês"},
    "tema": {"python": "Python", "automacao": "Automação", "dados": "Dados", "ia": "IA"},
}


def _temas_da_config(temas):
    """Nomes dos temas na ordem da config, sem repetir entre idiomas."""
    nomes = []
    for temas_do_idioma in temas.values():
        for nome in temas_do_idioma:
            if nome not in nomes:
                nomes.append(nome)
    return nomes


def opcoes_de_filtro(noticias, temas):
    """Opções de cada filtro como pares (valor, rótulo).

    Origem é fixa; fonte e idioma vêm das notícias (em ordem alfabética);
    tema vem da config.
    """
    def com_rotulo(campo, valores):
        return [(v, ROTULOS.get(campo, {}).get(v, v)) for v in valores]

    return {
        "origem": com_rotulo("origem", ["primaria", "comunidade"]),
        "fonte": com_rotulo("fonte", sorted({n.fonte for n in noticias})),
        "idioma": com_rotulo("idioma", sorted({n.idioma for n in noticias})),
        "tema": com_rotulo("tema", _temas_da_config(temas)),
    }


def filtros_validos(pedido, opcoes):
    """Mantém só os filtros cujo valor está entre as opções. O resto é ignorado.

    `pedido` vem da URL e pode ter qualquer coisa: valores desconhecidos não
    geram erro, simplesmente não filtram.
    """
    validos = {}
    for campo in CAMPOS:
        valor = pedido.get(campo, "")
        if valor and valor in {v for v, _ in opcoes[campo]}:
            validos[campo] = valor
    return validos


def aplicar_filtros(noticias, filtros, temas):
    """Devolve as notícias que passam em TODOS os filtros, na ordem original."""
    resultado = []
    for n in noticias:
        if "origem" in filtros and n.origem != filtros["origem"]:
            continue
        if "fonte" in filtros and n.fonte != filtros["fonte"]:
            continue
        if "idioma" in filtros and n.idioma != filtros["idioma"]:
            continue
        if "tema" in filtros and filtros["tema"] not in temas_da_noticia(n, temas):
            continue
        resultado.append(n)
    return resultado

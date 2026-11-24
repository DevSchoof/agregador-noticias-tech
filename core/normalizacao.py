"""Funções puras que deixam os dados de qualquer fonte num formato único.

Só usa a biblioteca padrão do Python (nada de rede, nada de feedparser).
"""

import re
import time
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

from core.modelo import NAO_INFORMADO

LIMITE_RESUMO = 300

# ------------------------------------------------------------------ HTML

# Tags que separam blocos de texto: viram espaço para as palavras não grudarem.
# Tags inline (b, a, em...) não viram espaço, para não criar "aqui ." antes da pontuação.
TAGS_DE_BLOCO = {
    "p", "br", "div", "li", "ul", "ol", "tr", "td", "th", "table",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "hr", "img",
}
# Tags cujo conteúdo não é texto para leitura.
TAGS_IGNORADAS = {"script", "style"}


class _ExtratorDeTexto(HTMLParser):
    """Percorre o HTML e guarda só o texto. As entidades (&amp;) já chegam convertidas."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self._dentro_de_ignorada = 0

    def handle_starttag(self, tag, attrs):
        if tag in TAGS_IGNORADAS:
            self._dentro_de_ignorada += 1
        elif tag in TAGS_DE_BLOCO:
            self.partes.append(" ")

    def handle_endtag(self, tag):
        if tag in TAGS_IGNORADAS:
            self._dentro_de_ignorada = max(0, self._dentro_de_ignorada - 1)
        elif tag in TAGS_DE_BLOCO:
            self.partes.append(" ")

    def handle_data(self, data):
        if not self._dentro_de_ignorada:
            self.partes.append(data)


def _juntar_espacos(texto):
    """Troca qualquer sequência de espaços, tabs e quebras de linha por um espaço só."""
    return " ".join(texto.split())


def limpar_html(texto):
    """Remove as tags HTML, converte entidades e junta os espaços."""
    if texto is None:
        return ""
    extrator = _ExtratorDeTexto()
    extrator.feed(str(texto))
    extrator.close()
    return _juntar_espacos("".join(extrator.partes))


def cortar_resumo(texto, limite=LIMITE_RESUMO):
    """Corta o texto em até `limite` caracteres, sem partir palavra, terminando em '…'."""
    if texto is None:
        return ""
    texto = texto.strip()
    if len(texto) <= limite:
        return texto

    # Reserva 1 caractere para o "…".
    pedaco = texto[: limite - 1]
    ultimo_espaco = pedaco.rfind(" ")
    if ultimo_espaco > 0:
        pedaco = pedaco[:ultimo_espaco]
    return pedaco.rstrip(" ,;:.") + "…"


# ------------------------------------------------------------------ Link

PARAMETROS_DE_RASTREIO = {"fbclid", "gclid", "msclkid", "mc_cid", "mc_eid", "igshid", "yclid"}


def _e_rastreio(nome_parametro):
    nome = nome_parametro.lower()
    return nome.startswith("utm_") or nome in PARAMETROS_DE_RASTREIO


def normalizar_link(link):
    """Deixa variantes do mesmo link iguais: domínio em minúsculas, sem rastreio,
    sem #fragmento e sem barra final. O caminho mantém maiúsculas (pode importar)."""
    if link is None:
        return ""
    partes = urlsplit(link.strip())

    # Filtra os parâmetros sem decodificar/recodificar, para não mudar o resto do link.
    parametros = [
        p for p in partes.query.split("&")
        if p and not _e_rastreio(p.split("=", 1)[0])
    ]

    return urlunsplit((
        partes.scheme.lower(),
        partes.netloc.lower(),
        partes.path.rstrip("/"),
        "&".join(parametros),
        "",  # fragmento descartado
    ))


# ------------------------------------------------------------------ Data

def _para_datetime(valor):
    """Converte os formatos de data que as fontes usam em datetime. None se não der."""
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, time.struct_time):  # feedparser (*_parsed), sempre em UTC
        return datetime(*valor[:6], tzinfo=timezone.utc)
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):  # Hacker News
        return datetime.fromtimestamp(valor, tz=timezone.utc)
    if isinstance(valor, str) and valor.strip():
        texto = valor.strip()
        try:
            return datetime.fromisoformat(texto)  # ISO 8601 (Atom, APIs)
        except ValueError:
            pass
        try:
            return parsedate_to_datetime(texto)  # RFC 822 (RSS)
        except (TypeError, ValueError):
            return None
    return None


def normalizar_data(valor):
    """Devolve a data em ISO 8601 no fuso UTC (AAAA-MM-DDTHH:MM:SS+00:00).

    Data sem fuso é tratada como UTC. Data ausente ou que não dá para ler
    vira NAO_INFORMADO.
    """
    data = _para_datetime(valor)
    if data is None:
        return NAO_INFORMADO
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    return data.astimezone(timezone.utc).replace(microsecond=0).isoformat()


# ------------------------------------------------------------------ Texto

def remover_acentos(texto):
    """'Ação' -> 'Acao'. Separa a letra do acento (NFKD) e descarta o acento."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar_texto(texto):
    """Versão para comparar textos: sem acento, sem caixa, sem pontuação."""
    if texto is None:
        return ""
    texto = remover_acentos(str(texto)).casefold()
    texto = re.sub(r"[^\w\s]", " ", texto)
    return _juntar_espacos(texto)

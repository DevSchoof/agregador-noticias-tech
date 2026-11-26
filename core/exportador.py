"""Gravação e leitura das notícias em arquivo: JSON (o histórico) e CSV (para Excel)."""

import csv
import json
from dataclasses import asdict, fields
from io import StringIO
from pathlib import Path

from core.modelo import Noticia

COLUNAS = [campo.name for campo in fields(Noticia)]  # ordem do contrato

# Segurança (CSV injection): no Excel, uma célula que começa com um destes
# caracteres é interpretada como fórmula. Título, resumo e tags vêm de terceiros.
INICIOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _gravar_com_seguranca(caminho, conteudo, encoding):
    """Grava primeiro num arquivo temporário e só depois troca pelo definitivo.

    Se o programa cair no meio da gravação, o arquivo antigo continua inteiro,
    em vez de ficar um JSON pela metade (que faria perder o histórico).
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    try:
        # newline="": o texto já vem com as quebras de linha certas (o csv usa \r\n).
        temporario.write_text(conteudo, encoding=encoding, newline="")
        temporario.replace(caminho)  # troca atômica no mesmo disco
    finally:
        temporario.unlink(missing_ok=True)


def salvar_json(noticias, caminho):
    """Salva a lista como JSON em UTF-8, com acentos legíveis e tags como lista."""
    dados = [asdict(n) for n in noticias]
    conteudo = json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
    _gravar_com_seguranca(caminho, conteudo, encoding="utf-8")


def carregar_json(caminho):
    """Lê o JSON salvo e devolve objetos Noticia. Arquivo inexistente = lista vazia.

    Campos que faltam (JSON de uma versão anterior) recebem o valor padrão do modelo.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        return []
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return [Noticia(**item) for item in dados]


def _proteger_celula(valor):
    """Põe um ' na frente do texto que o Excel executaria como fórmula.

    O ' é o jeito do próprio Excel de dizer "isto é texto". Só o CSV recebe a
    proteção; o JSON guarda o texto exatamente como veio da fonte.
    """
    if isinstance(valor, str) and valor.startswith(INICIOS_DE_FORMULA):
        return "'" + valor
    return valor


def salvar_csv(noticias, caminho):
    """Salva como CSV em utf-8-sig (o BOM faz o Excel reconhecer os acentos).

    Tags viram texto separado por vírgula. O módulo csv coloca aspas nos textos
    que têm vírgula ou aspas, para não quebrar as colunas.
    """
    linhas = []
    for noticia in noticias:
        linha = asdict(noticia)
        linha["tags"] = ", ".join(noticia.tags)
        linhas.append({coluna: _proteger_celula(valor) for coluna, valor in linha.items()})

    # Monta o CSV em memória para reaproveitar a gravação segura.
    buffer = StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=COLUNAS)
    escritor.writeheader()
    escritor.writerows(linhas)
    _gravar_com_seguranca(caminho, buffer.getvalue(), encoding="utf-8-sig")

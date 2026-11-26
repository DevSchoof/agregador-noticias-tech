"""Gravação e leitura das notícias em arquivo: JSON (o histórico) e CSV (para Excel)."""

import csv
import json
from dataclasses import asdict, fields
from io import StringIO
from pathlib import Path

from core.modelo import Noticia

COLUNAS = [campo.name for campo in fields(Noticia)]  # ordem do contrato


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


def salvar_csv(noticias, caminho):
    """Salva como CSV em utf-8-sig (o BOM faz o Excel reconhecer os acentos).

    Tags viram texto separado por vírgula. O módulo csv coloca aspas nos textos
    que têm vírgula ou aspas, para não quebrar as colunas.
    """
    linhas = []
    for noticia in noticias:
        linha = asdict(noticia)
        linha["tags"] = ", ".join(noticia.tags)
        linhas.append(linha)

    # Monta o CSV em memória para reaproveitar a gravação segura.
    buffer = StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=COLUNAS)
    escritor.writeheader()
    escritor.writerows(linhas)
    _gravar_com_seguranca(caminho, buffer.getvalue(), encoding="utf-8-sig")

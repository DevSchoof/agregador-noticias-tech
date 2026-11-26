"""Ponto de entrada: python main.py

Fluxo: config -> cada fonte coleta -> filtro (se a fonte pedir) -> junta com o
que já está salvo -> deduplica e ordena -> salva JSON e CSV.
"""

import logging
import sys
import time
from pathlib import Path

from config.fontes import FONTES, PAUSA_ENTRE_FONTES
from config.temas import TEMAS
from core.deduplicador import deduplicar
from core.exportador import carregar_json, salvar_csv, salvar_json
from core.filtro import descartar_pre_versoes, filtrar_por_tema
from fontes.rss_generico import RssGenerico

PASTA_PROJETO = Path(__file__).parent
PASTA_DADOS = PASTA_PROJETO / "dados"
PASTA_LOGS = PASTA_PROJETO / "logs"

logger = logging.getLogger("agregador")


def criar_fonte(cfg):
    """Transforma uma entrada de config/fontes.py no objeto da fonte."""
    if cfg.get("tipo") == "rss":
        return RssGenerico(nome=cfg["nome"], url=cfg["url"],
                           idioma=cfg["idioma"], origem=cfg["origem"])
    raise ValueError(f"tipo de fonte desconhecido: {cfg.get('tipo')!r}")


def _coletar_todas(configs, temas, fabrica, pausa):
    """Roda cada fonte isolada num try/except: se uma falha, as outras seguem."""
    coletadas, aproveitadas, falhas = 0, [], []
    for posicao, cfg in enumerate(configs):
        if posicao > 0 and pausa:
            time.sleep(pausa)
        nome = cfg["nome"]
        try:
            noticias = fabrica(cfg).coletar()
        except Exception:
            # logger.exception grava a mensagem e o traceback no log.
            logger.exception("Fonte %r falhou; seguindo com as outras.", nome)
            falhas.append(nome)
            continue

        total_da_fonte = len(noticias)
        coletadas += total_da_fonte
        if cfg.get("descartar_pre_versoes", False):
            noticias = descartar_pre_versoes(noticias)
        if cfg["filtrar"]:
            noticias = filtrar_por_tema(noticias, temas)
        logger.info("Fonte %r: %d coletadas, %d aproveitadas%s.", nome,
                    total_da_fonte, len(noticias),
                    "" if cfg["filtrar"] else " (sem filtro de temas)")
        aproveitadas.extend(noticias)
    return coletadas, aproveitadas, falhas


def executar(configs, pasta_dados=PASTA_DADOS, temas=TEMAS, fabrica=criar_fonte,
             pausa=PAUSA_ENTRE_FONTES):
    """Executa uma coleta completa e devolve um resumo com as contagens.

    O JSON salvo é lido ANTES de coletar: se estiver corrompido, a execução para
    com erro e o arquivo não é sobrescrito (o histórico não se perde).
    """
    pasta_dados = Path(pasta_dados)
    caminho_json = pasta_dados / "noticias.json"
    salvas = carregar_json(caminho_json)

    coletadas, novas, falhas = _coletar_todas(configs, temas, fabrica, pausa)

    # Salvas primeiro: em empate, o deduplicador mantém a que já estava salva.
    resultado = deduplicar(salvas + novas)
    salvar_json(resultado, caminho_json)
    salvar_csv(resultado, pasta_dados / "noticias.csv")

    return {
        "coletadas": coletadas,
        "depois_do_filtro": len(novas),
        "repetidas": len(salvas) + len(novas) - len(resultado),
        "total_salvo": len(resultado),
        "falhas": falhas,
    }


def configurar_logging():
    """Log no arquivo logs/agregador.log (UTF-8) e também na tela."""
    PASTA_LOGS.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(PASTA_LOGS / "agregador.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main():
    configurar_logging()
    logger.info("Início da coleta (%d fontes).", len(FONTES))
    try:
        resumo = executar(FONTES)
    except Exception:
        logger.exception("Execução interrompida; nada foi salvo.")
        return 1
    logger.info("Fim: %s", resumo)
    return 0


if __name__ == "__main__":
    sys.exit(main())

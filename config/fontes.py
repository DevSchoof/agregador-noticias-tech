"""Quais fontes rodam e com quais parâmetros. Para desligar uma fonte, comente-a.

Campos de cada fonte:
- tipo: qual classe de fontes/ cuida dela ("rss" = RSS ou Atom).
- nome: aparece no campo `fonte` de cada notícia e no log.
- url: endereço do feed (só feeds oficiais, ver seção 4 do CLAUDE.md).
- idioma: "pt" ou "en".
- origem: "primaria" ou "comunidade".
- filtrar: True para fontes gerais (passam pelo filtro de temas); False para
  fontes que já são do tema (títulos como "8.3.4" seriam descartados).
- descartar_pre_versoes (opcional, padrão False): True nas releases, para não
  salvar nightly, alpha, beta, rc, dev (decisão do Eduardo em 2026-11-26).
"""

FONTES = [
    {
        "tipo": "rss",
        "nome": "Python Insider",
        "url": "https://blog.python.org/rss.xml",
        "idioma": "en",
        "origem": "primaria",
        "filtrar": False,
    },
    {
        "tipo": "rss",
        "nome": "Releases do Selenium",
        "url": "https://github.com/SeleniumHQ/selenium/releases.atom",
        "idioma": "en",
        "origem": "primaria",
        "filtrar": False,
        "descartar_pre_versoes": True,
    },
    {
        "tipo": "rss",
        "nome": "Releases do pytest",
        "url": "https://github.com/pytest-dev/pytest/releases.atom",
        "idioma": "en",
        "origem": "primaria",
        "filtrar": False,
        "descartar_pre_versoes": True,
    },
]

# Pausa (segundos) entre uma fonte e a próxima, para não fazer chamadas em
# sequência ao mesmo site (as duas de releases são do github.com).
PAUSA_ENTRE_FONTES = 2

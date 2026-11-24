"""Palavras-chave de cada tema, separadas por idioma.

Por que separar por idioma: sem acento, o "aí" do português vira "ai", e o
"data" do português é "data" de calendário. Cada notícia é comparada só com
as palavras do seu idioma.

Regras de escrita: pode usar acento e maiúsculas (o filtro ignora os dois).
A comparação é por palavra/expressão inteira: "automação" não casa com
"automatizado", por isso algumas formas aparecem mais de uma vez.
"""

TEMAS = {
    "pt": {
        "python": ["python", "pytest", "django", "flask", "fastapi", "pypi"],
        "automacao": [
            "automação", "automatização", "automatizar", "automatizado",
            "automatizada", "rpa", "selenium", "playwright", "web scraping",
            "raspagem de dados",
        ],
        # Sem "dados" sozinho: em notícias de economia ("segundo dados do IBGE")
        # quase tudo casaria.
        "dados": [
            "ciência de dados", "cientista de dados", "análise de dados",
            "engenharia de dados", "banco de dados", "bancos de dados",
            "big data", "dados abertos", "proteção de dados",
            "vazamento de dados", "lgpd", "sql", "pandas", "etl",
        ],
        "ia": [
            "ia", "inteligência artificial", "aprendizado de máquina",
            "machine learning", "deep learning", "rede neural", "redes neurais",
            "llm", "chatbot",
        ],
    },
    "en": {
        "python": ["python", "pytest", "django", "flask", "fastapi", "pypi", "pip"],
        "automacao": [
            "automation", "automate", "automated", "rpa", "selenium",
            "playwright", "web scraping",
        ],
        "dados": [
            "data science", "data scientist", "data engineering",
            "data analysis", "data pipeline", "database", "databases",
            "big data", "open data", "sql", "pandas", "etl",
        ],
        "ia": [
            "ai", "artificial intelligence", "machine learning",
            "deep learning", "neural network", "neural networks",
            "llm", "llms", "generative ai", "chatbot",
        ],
    },
}

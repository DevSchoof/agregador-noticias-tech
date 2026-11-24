"""Contrato de dados do agregador: o formato de toda notícia, venha de qual fonte vier."""

from dataclasses import dataclass, field

NAO_INFORMADO = "não informado"

ORIGENS_VALIDAS = ("primaria", "comunidade")
IDIOMAS_VALIDOS = ("pt", "en")


def _ou_nao_informado(valor):
    """Devolve o próprio valor, ou NAO_INFORMADO se ele for None ou texto vazio."""
    if valor is None or str(valor).strip() == "":
        return NAO_INFORMADO
    return valor


# kw_only=True: os campos só podem ser passados por nome (titulo=..., link=...),
# o que evita trocar dois campos de lugar sem perceber.
@dataclass(kw_only=True)
class Noticia:
    titulo: str
    link: str
    fonte: str
    data_publicacao: str = NAO_INFORMADO
    resumo: str = NAO_INFORMADO
    # default_factory cria uma lista nova para cada notícia (uma lista como
    # padrão direto seria a mesma para todas).
    tags: list[str] = field(default_factory=list)
    idioma: str
    area: str = "tech"
    origem: str

    def __post_init__(self):
        """Roda logo depois da criação: valida e preenche os campos ausentes."""
        if self.link is None or str(self.link).strip() == "":
            raise ValueError("Notícia sem link: o link é obrigatório.")
        if self.origem not in ORIGENS_VALIDAS:
            raise ValueError(f"origem inválida: {self.origem!r}. Use {ORIGENS_VALIDAS}.")
        if self.idioma not in IDIOMAS_VALIDOS:
            raise ValueError(f"idioma inválido: {self.idioma!r}. Use {IDIOMAS_VALIDOS}.")

        self.titulo = _ou_nao_informado(self.titulo)
        self.fonte = _ou_nao_informado(self.fonte)
        self.data_publicacao = _ou_nao_informado(self.data_publicacao)
        self.resumo = _ou_nao_informado(self.resumo)
        if self.tags is None:
            self.tags = []

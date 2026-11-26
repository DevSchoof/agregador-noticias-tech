"""Page Object da página de notícias.

A ideia do padrão: os testes falam a língua do usuário ("filtrar por tema",
"ler os títulos"), e só esta classe conhece os seletores e o jeito de esperar
a página. Se o HTML mudar, ajusta-se aqui, e os testes continuam iguais.

Seletores: sempre pelos atributos data-testid, que existem só para testes e
não mudam quando o visual muda.

Esperas: explícitas (WebDriverWait), nunca time.sleep. O teste espera
exatamente a condição de que precisa, nem mais nem menos tempo.
"""

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as condicao
from selenium.webdriver.support.ui import Select, WebDriverWait

TEMPO_MAXIMO = 10  # segundos


def _testid(nome):
    return (By.CSS_SELECTOR, f'[data-testid="{nome}"]')


def esperar_troca_de_pagina(navegador, elemento_antigo, tempo=TEMPO_MAXIMO, intervalo=0.5):
    """Espera o elemento da página antiga deixar de existir (página trocada).

    No meio da troca, o Chrome às vezes responde com um erro genérico ("Node with
    given id does not belong to the document") em vez de dizer que o elemento
    sumiu. Esse erro é tratado como "ainda trocando": a espera pergunta de novo.
    Se a página nunca trocar, o tempo esgota e o teste falha (TimeoutException),
    então um defeito real não fica escondido.
    """
    espera = WebDriverWait(navegador, tempo, poll_frequency=intervalo,
                           ignored_exceptions=(WebDriverException,))
    return espera.until(condicao.staleness_of(elemento_antigo))


class PaginaNoticias:
    TITULO = _testid("titulo")
    ORIGEM = _testid("origem")
    TOTAL = _testid("total")
    FORMULARIO = _testid("filtros")
    BOTAO_FILTRAR = _testid("filtrar")
    LIMPAR = _testid("limpar")
    SEM_RESULTADO = _testid("sem-resultado")

    def __init__(self, navegador, url_base):
        self.navegador = navegador
        self.url_base = url_base.rstrip("/")
        self.espera = WebDriverWait(navegador, TEMPO_MAXIMO)

    # ------------------------------------------------------- navegação

    def abrir(self, caminho="/"):
        self.navegador.get(self.url_base + caminho)
        self.espera.until(condicao.visibility_of_element_located(self.FORMULARIO))
        return self

    def _clicar_e_esperar_recarregar(self, localizador):
        """Clica num elemento que recarrega a página e espera a página nova.

        "staleness" = o elemento antigo deixou de existir, ou seja, a página
        foi trocada. Depois espera o formulário da página nova aparecer.
        """
        pagina_antiga = self.navegador.find_element(By.TAG_NAME, "html")
        self.navegador.find_element(*localizador).click()
        esperar_troca_de_pagina(self.navegador, pagina_antiga)
        self.espera.until(condicao.visibility_of_element_located(self.FORMULARIO))

    def url(self):
        return self.navegador.current_url

    # --------------------------------------------------------- filtros

    def _caixa(self, campo):
        return Select(self.navegador.find_element(*_testid(f"filtro-{campo}")))

    def filtrar(self, **filtros):
        """Ex.: filtrar(origem="comunidade", tema="ia"). Usa o VALOR da opção."""
        for campo, valor in filtros.items():
            self._caixa(campo).select_by_value(valor)
        self._clicar_e_esperar_recarregar(self.BOTAO_FILTRAR)
        return self

    def limpar_filtros(self):
        self._clicar_e_esperar_recarregar(self.LIMPAR)
        return self

    def filtro_selecionado(self, campo):
        """Valor da opção escolhida ("" = todos)."""
        return self._caixa(campo).first_selected_option.get_attribute("value")

    # ---------------------------------------------------------- leitura

    def titulos(self):
        return [e.text for e in self.navegador.find_elements(*self.TITULO)]

    def origens(self):
        return [e.text for e in self.navegador.find_elements(*self.ORIGEM)]

    def total(self):
        return self.navegador.find_element(*self.TOTAL).text

    def mensagem_sem_resultado(self):
        """Texto do aviso de "nenhuma notícia", ou "" se não houver aviso."""
        avisos = self.navegador.find_elements(*self.SEM_RESULTADO)
        return avisos[0].text if avisos else ""

    def link_de(self, titulo):
        """Atributos do link de uma notícia, achada pelo título."""
        for elemento in self.navegador.find_elements(*self.TITULO):
            if elemento.text == titulo:
                return {atributo: elemento.get_attribute(atributo)
                        for atributo in ("href", "target", "rel")}
        raise LookupError(f"Notícia não encontrada na página: {titulo!r}")

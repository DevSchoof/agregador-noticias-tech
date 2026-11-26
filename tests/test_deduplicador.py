"""Testes do deduplicador. Dados fictícios.

A lista de entrada simula o que o main faz: primeiro as notícias já salvas,
depois as recém-coletadas.
"""

from core.deduplicador import deduplicar
from core.modelo import NAO_INFORMADO, Noticia


def criar(titulo="Título fictício", link="https://exemplo.com/a", origem="primaria",
          data="2026-11-16T10:00:00+00:00", fonte="Fonte Fictícia", **outros):
    return Noticia(
        titulo=titulo, link=link, fonte=fonte, data_publicacao=data,
        idioma="en", origem=origem, **outros,
    )


def links(noticias):
    return [n.link for n in noticias]


# ------------------------------------------------------- nível 1: link

def test_variantes_do_mesmo_link_viram_uma_noticia_so():
    a = criar(link="https://exemplo.com/a")
    b = criar(link="https://EXEMPLO.com/a/?utm_source=feed#topo")

    assert links(deduplicar([a, b])) == ["https://exemplo.com/a"]


def test_link_igual_fica_a_primaria_mesmo_vindo_depois():
    comunidade = criar(origem="comunidade", fonte="Comunidade Fictícia")
    primaria = criar(origem="primaria", fonte="Blog Oficial Fictício")

    resultado = deduplicar([comunidade, primaria])

    assert len(resultado) == 1
    assert resultado[0].origem == "primaria"
    assert resultado[0].fonte == "Blog Oficial Fictício"


def test_link_igual_fica_a_primaria_vindo_antes():
    primaria = criar(origem="primaria")
    comunidade = criar(origem="comunidade")

    assert [n.origem for n in deduplicar([primaria, comunidade])] == ["primaria"]


def test_link_igual_e_mesma_origem_fica_a_que_ja_estava_salva():
    salva = criar(resumo="Resumo da versão salva")
    nova = criar(resumo="Resumo da versão nova")

    assert [n.resumo for n in deduplicar([salva, nova])] == ["Resumo da versão salva"]


def test_noticias_diferentes_ficam_todas():
    a = criar(titulo="Primeira", link="https://exemplo.com/1")
    b = criar(titulo="Segunda", link="https://exemplo.com/2")

    resultado = deduplicar([a, b])

    assert len(resultado) == 2
    assert all(n.provavel_duplicata_de == "" for n in resultado)


# ------------------------------------------------------- nível 2: título

def test_titulo_igual_com_link_diferente_marca_a_comunidade():
    primaria = criar(titulo="Python 9.9 lançado", link="https://blog-ficticio.org/py99")
    comunidade = criar(titulo="Python 9.9 lançado", link="https://forum-ficticio.com/item/1",
                       origem="comunidade")

    resultado = {n.link: n for n in deduplicar([comunidade, primaria])}

    assert len(resultado) == 2  # marca, não apaga
    assert resultado["https://blog-ficticio.org/py99"].provavel_duplicata_de == ""
    assert (resultado["https://forum-ficticio.com/item/1"].provavel_duplicata_de
            == "https://blog-ficticio.org/py99")


def test_titulo_igual_ignorando_acento_caixa_e_pontuacao():
    a = criar(titulo="Automação em alta!", link="https://exemplo.com/1")
    b = criar(titulo="automacao em ALTA", link="https://exemplo.com/2")

    marcadas = [n for n in deduplicar([a, b]) if n.provavel_duplicata_de]

    assert len(marcadas) == 1


def test_titulo_igual_na_mesma_origem_a_mais_antiga_e_a_principal():
    nova = criar(titulo="Mesmo título", link="https://exemplo.com/nova",
                 data="2026-11-20T10:00:00+00:00")
    antiga = criar(titulo="Mesmo título", link="https://exemplo.com/antiga",
                   data="2026-11-10T10:00:00+00:00")

    resultado = {n.link: n for n in deduplicar([nova, antiga])}

    assert resultado["https://exemplo.com/antiga"].provavel_duplicata_de == ""
    assert resultado["https://exemplo.com/nova"].provavel_duplicata_de == "https://exemplo.com/antiga"


def test_titulo_igual_com_data_ganha_de_sem_data():
    sem_data = criar(titulo="Mesmo título", link="https://exemplo.com/1", data=NAO_INFORMADO)
    com_data = criar(titulo="Mesmo título", link="https://exemplo.com/2")

    resultado = {n.link: n for n in deduplicar([sem_data, com_data])}

    assert resultado["https://exemplo.com/1"].provavel_duplicata_de == "https://exemplo.com/2"


def test_titulo_igual_sem_data_nas_duas_fica_a_que_ja_estava_salva():
    salva = criar(titulo="Mesmo título", link="https://exemplo.com/1", data=NAO_INFORMADO)
    nova = criar(titulo="Mesmo título", link="https://exemplo.com/2", data=NAO_INFORMADO)

    resultado = {n.link: n for n in deduplicar([salva, nova])}

    assert resultado["https://exemplo.com/2"].provavel_duplicata_de == "https://exemplo.com/1"


def test_tres_com_mesmo_titulo_apontam_para_a_mesma_principal():
    principal = criar(titulo="Mesmo título", link="https://exemplo.com/1")
    outras = [
        criar(titulo="Mesmo título", link=f"https://exemplo.com/{i}", origem="comunidade")
        for i in (2, 3)
    ]

    marcas = [n.provavel_duplicata_de for n in deduplicar([*outras, principal])]

    assert sorted(marcas) == ["", "https://exemplo.com/1", "https://exemplo.com/1"]


def test_titulo_nao_informado_nao_conta_como_igual():
    a = criar(titulo=None, link="https://exemplo.com/1")
    b = criar(titulo=None, link="https://exemplo.com/2")

    assert all(n.provavel_duplicata_de == "" for n in deduplicar([a, b]))


# ------------------------------------------------ entre execuções

def test_primaria_que_chega_depois_substitui_comunidade_com_mesmo_link():
    salva_ontem = [criar(origem="comunidade", fonte="Comunidade Fictícia")]
    coletada_hoje = [criar(origem="primaria", fonte="Blog Oficial Fictício")]

    resultado = deduplicar(salva_ontem + coletada_hoje)

    assert [n.fonte for n in resultado] == ["Blog Oficial Fictício"]


def test_primaria_que_chega_depois_vira_principal_de_titulo_igual():
    salva_ontem = [criar(titulo="Mesmo título", link="https://forum-ficticio.com/1",
                         origem="comunidade")]
    coletada_hoje = [criar(titulo="Mesmo título", link="https://blog-ficticio.org/1")]

    resultado = {n.link: n for n in deduplicar(salva_ontem + coletada_hoje)}

    assert (resultado["https://forum-ficticio.com/1"].provavel_duplicata_de
            == "https://blog-ficticio.org/1")


def test_marca_antiga_e_recalculada_do_zero():
    # Salva marcada numa execução anterior, mas a principal não existe mais na lista.
    marcada = criar(link="https://exemplo.com/1",
                    provavel_duplicata_de="https://exemplo.com/sumiu")

    assert deduplicar([marcada])[0].provavel_duplicata_de == ""


def test_nao_altera_as_noticias_de_entrada():
    a = criar(titulo="Mesmo título", link="https://exemplo.com/1")
    b = criar(titulo="Mesmo título", link="https://exemplo.com/2", origem="comunidade")

    deduplicar([a, b])

    assert b.provavel_duplicata_de == ""


# ------------------------------------------------------- ordenação

def test_ordena_primarias_primeiro_e_mais_nova_primeiro():
    c_antiga = criar(titulo="c1", link="https://exemplo.com/c1", origem="comunidade",
                     data="2026-11-01T10:00:00+00:00")
    p_antiga = criar(titulo="p1", link="https://exemplo.com/p1",
                     data="2026-11-02T10:00:00+00:00")
    c_nova = criar(titulo="c2", link="https://exemplo.com/c2", origem="comunidade",
                   data="2026-11-20T10:00:00+00:00")
    p_nova = criar(titulo="p2", link="https://exemplo.com/p2",
                   data="2026-11-15T10:00:00+00:00")

    resultado = deduplicar([c_antiga, p_antiga, c_nova, p_nova])

    assert [n.titulo for n in resultado] == ["p2", "p1", "c2", "c1"]


def test_sem_data_vai_para_o_fim_do_seu_grupo():
    sem_data = criar(titulo="sem data", link="https://exemplo.com/1", data=NAO_INFORMADO)
    com_data = criar(titulo="com data", link="https://exemplo.com/2")
    comunidade = criar(titulo="comunidade", link="https://exemplo.com/3", origem="comunidade")

    resultado = deduplicar([sem_data, comunidade, com_data])

    assert [n.titulo for n in resultado] == ["com data", "sem data", "comunidade"]


def test_lista_vazia():
    assert deduplicar([]) == []

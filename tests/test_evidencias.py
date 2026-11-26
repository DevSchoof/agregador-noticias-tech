"""Testes da função que salva print e HTML quando um teste E2E falha.

Usa um navegador FALSO (só tem os dois métodos que a função usa), então
roda na suíte rápida, sem Selenium de verdade.
"""

from tests.e2e.evidencias import nome_de_arquivo_seguro, salvar_evidencias


class NavegadorFalso:
    page_source = "<html><body>página fictícia com acentuação</body></html>"

    def save_screenshot(self, caminho):
        with open(caminho, "wb") as arquivo:
            arquivo.write(b"PNG-falso")
        return True


def test_salva_print_e_html(tmp_path):
    arquivos = salvar_evidencias(NavegadorFalso(), tmp_path / "evidencias",
                                 "test_lista[chrome]")

    png, html = arquivos
    assert png.name == "test_lista_chrome_.png"
    assert html.name == "test_lista_chrome_.html"
    assert png.read_bytes() == b"PNG-falso"
    assert html.read_text(encoding="utf-8") == NavegadorFalso.page_source


def test_cria_a_pasta_se_nao_existir(tmp_path):
    pasta = tmp_path / "a" / "b"

    salvar_evidencias(NavegadorFalso(), pasta, "teste")

    assert pasta.is_dir()


def test_falha_ao_salvar_nao_esconde_a_falha_do_teste(tmp_path):
    # Se o navegador já fechou, salvar a evidência falha; isso não pode gerar
    # um erro novo que esconda o motivo original da falha do teste.
    class NavegadorFechado:
        @property
        def page_source(self):
            raise RuntimeError("navegador fechado")

        def save_screenshot(self, caminho):
            raise RuntimeError("navegador fechado")

    assert salvar_evidencias(NavegadorFechado(), tmp_path, "teste") == []


def test_nome_de_arquivo_seguro():
    assert nome_de_arquivo_seguro("test_filtro[firefox-tema=ia]") == "test_filtro_firefox-tema_ia_"
    assert nome_de_arquivo_seguro("../../etc/passwd") == ".._.._etc_passwd"
    assert nome_de_arquivo_seguro("acentuação ok") == "acentuação_ok"

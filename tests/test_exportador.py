"""Testes do exportador (JSON e CSV). Usa a pasta temporária do pytest (tmp_path)."""

import csv
import json
from dataclasses import fields

from core.deduplicador import deduplicar
from core.exportador import carregar_json, salvar_csv, salvar_json
from core.modelo import NAO_INFORMADO, Noticia


def criar(titulo="Automação fictícia em alta", link="https://exemplo.com/a",
          origem="primaria", **outros):
    return Noticia(
        titulo=titulo, link=link, fonte="Fonte Fictícia",
        data_publicacao="2026-11-16T10:00:00+00:00", idioma="pt",
        origem=origem, **outros,
    )


COLUNAS = [f.name for f in fields(Noticia)]


# ------------------------------------------------------------------ JSON

def test_json_salvar_e_carregar_devolve_as_mesmas_noticias(tmp_path):
    caminho = tmp_path / "noticias.json"
    noticias = [
        criar(tags=["python", "dados"]),
        criar(titulo="Outra", link="https://exemplo.com/b", origem="comunidade",
              provavel_duplicata_de="https://exemplo.com/a"),
    ]

    salvar_json(noticias, caminho)

    assert carregar_json(caminho) == noticias


def test_json_e_valido_e_tags_sao_lista(tmp_path):
    caminho = tmp_path / "noticias.json"
    salvar_json([criar(tags=["python", "dados"])], caminho)

    dados = json.loads(caminho.read_text(encoding="utf-8"))

    assert isinstance(dados, list)
    assert dados[0]["tags"] == ["python", "dados"]
    assert list(dados[0]) == COLUNAS


def test_json_guarda_acentos_legiveis(tmp_path):
    caminho = tmp_path / "noticias.json"
    salvar_json([criar()], caminho)

    texto = caminho.read_text(encoding="utf-8")

    assert "Automação fictícia" in texto  # e não "Automa\u00e7\u00e3o"


def test_json_lista_vazia(tmp_path):
    caminho = tmp_path / "noticias.json"
    salvar_json([], caminho)

    assert carregar_json(caminho) == []


def test_carregar_json_inexistente_devolve_lista_vazia(tmp_path):
    assert carregar_json(tmp_path / "nao_existe.json") == []


def test_carregar_json_antigo_sem_campo_novo(tmp_path):
    # JSON salvo antes de existir o campo provavel_duplicata_de.
    caminho = tmp_path / "noticias.json"
    antigo = {
        "titulo": "Título fictício", "link": "https://exemplo.com/a",
        "fonte": "Fonte Fictícia", "data_publicacao": NAO_INFORMADO,
        "resumo": NAO_INFORMADO, "tags": [], "idioma": "pt", "area": "tech",
        "origem": "primaria",
    }
    caminho.write_text(json.dumps([antigo]), encoding="utf-8")

    assert carregar_json(caminho)[0].provavel_duplicata_de == ""


def test_salvar_cria_a_pasta_se_nao_existir(tmp_path):
    caminho = tmp_path / "dados" / "sub" / "noticias.json"
    salvar_json([criar()], caminho)

    assert caminho.exists()


def test_salvar_nao_deixa_arquivo_temporario(tmp_path):
    salvar_json([criar()], tmp_path / "noticias.json")
    salvar_csv([criar()], tmp_path / "noticias.csv")

    assert sorted(p.name for p in tmp_path.iterdir()) == ["noticias.csv", "noticias.json"]


def test_salvar_sobrescreve_o_arquivo_anterior(tmp_path):
    caminho = tmp_path / "noticias.json"
    salvar_json([criar(), criar(link="https://exemplo.com/b")], caminho)
    salvar_json([criar()], caminho)

    assert len(carregar_json(caminho)) == 1


# ------------------------------------------------------------------- CSV

def ler_csv(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def test_csv_comeca_com_bom_para_o_excel(tmp_path):
    caminho = tmp_path / "noticias.csv"
    salvar_csv([criar()], caminho)

    assert caminho.read_bytes().startswith(b"\xef\xbb\xbf")


def test_csv_tem_cabecalho_na_ordem_do_contrato(tmp_path):
    caminho = tmp_path / "noticias.csv"
    salvar_csv([criar()], caminho)

    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        assert next(csv.reader(arquivo)) == COLUNAS


def test_csv_uma_linha_por_noticia_com_tags_separadas_por_virgula(tmp_path):
    caminho = tmp_path / "noticias.csv"
    salvar_csv([criar(tags=["python", "dados"]),
                criar(link="https://exemplo.com/b")], caminho)

    linhas = ler_csv(caminho)

    assert len(linhas) == 2
    assert linhas[0]["tags"] == "python, dados"
    assert linhas[1]["tags"] == ""
    assert linhas[0]["titulo"] == "Automação fictícia em alta"


def test_csv_texto_com_virgula_e_aspas_nao_quebra_colunas(tmp_path):
    caminho = tmp_path / "noticias.csv"
    titulo = 'Python, dados e "IA": o que muda'
    salvar_csv([criar(titulo=titulo)], caminho)

    assert ler_csv(caminho)[0]["titulo"] == titulo


def test_csv_lista_vazia_tem_so_o_cabecalho(tmp_path):
    caminho = tmp_path / "noticias.csv"
    salvar_csv([], caminho)

    assert ler_csv(caminho) == []
    assert caminho.read_text(encoding="utf-8-sig").strip() == ",".join(COLUNAS)


# ------------------------------------------- duas execuções (acumular)

def test_duas_execucoes_acumulam_sem_repetir(tmp_path):
    caminho = tmp_path / "noticias.json"

    # Execução 1: só a versão de comunidade.
    primeira = [criar(titulo="Notícia A", link="https://exemplo.com/a?utm_source=hn",
                      origem="comunidade")]
    salvar_json(deduplicar(carregar_json(caminho) + primeira), caminho)

    # Execução 2: chega a primária com o mesmo link e uma notícia nova.
    segunda = [
        criar(titulo="Notícia A", link="https://exemplo.com/a"),
        criar(titulo="Notícia B", link="https://exemplo.com/b"),
    ]
    salvar_json(deduplicar(carregar_json(caminho) + segunda), caminho)

    resultado = carregar_json(caminho)
    assert sorted(n.titulo for n in resultado) == ["Notícia A", "Notícia B"]
    assert all(n.origem == "primaria" for n in resultado)

    # Execução 3: nada de novo, nada muda.
    salvar_json(deduplicar(carregar_json(caminho) + segunda), caminho)
    assert carregar_json(caminho) == resultado

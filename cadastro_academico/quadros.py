"""Criação e validação dos DataFrames usados pela carga."""

import pandas as pd

COLUNAS = {
    "alunos": ["codigo_origem", "nome", "email"],
    "cursos": ["nome"],
    "matriculas": ["numero_matricula", "aluno_codigo_origem", "curso_nome"],
}


def criar_dataframes(dados):
    quadros = {}
    for tabela, colunas in COLUNAS.items():
        quadro = pd.DataFrame.from_records(dados[tabela], columns=colunas)
        if quadro.isna().any().any():
            raise ValueError(f"Há campos obrigatórios ausentes no DataFrame {tabela}.")
        quadros[tabela] = quadro.astype("string")

    alunos, cursos, matriculas = (quadros[nome] for nome in COLUNAS)
    for quadro, coluna in (
        (alunos, "codigo_origem"), (alunos, "email"),
        (cursos, "nome"), (matriculas, "numero_matricula"),
    ):
        if quadro[coluna].duplicated().any():
            raise ValueError(f"Valores duplicados na coluna {coluna}.")
    if matriculas.duplicated(["aluno_codigo_origem", "curso_nome"]).any():
        raise ValueError("Há vínculos aluno/curso duplicados.")
    if not matriculas["aluno_codigo_origem"].isin(alunos["codigo_origem"]).all():
        raise ValueError("Há matrícula sem aluno correspondente.")
    if not matriculas["curso_nome"].isin(cursos["nome"]).all():
        raise ValueError("Há matrícula sem curso correspondente.")
    return quadros

"""Persistência dos DataFrames e histórico das execuções."""

import pandas as pd
from psycopg.types.json import Jsonb
from psycopg.pq import TransactionStatus


def iniciar_ingestao(conexao, parametros):
    return conexao.execute(
        """insert into public.ingestoes (fonte, parametros)
           values ('randomuser', %s) returning id_ingestao""",
        (Jsonb(parametros),),
    ).fetchone()[0]


def finalizar_ingestao(conexao, id_ingestao, recebidos, gravados=0, erro=None):
    conexao.execute(
        """update public.ingestoes
           set status = %s, dt_fim = statement_timestamp(),
               quantidade_registros_recebidos = %s, quantidade_registros_gravados = %s,
               mensagem_erro = %s
           where id_ingestao = %s""",
        ("falhou" if erro is not None else "concluida", recebidos, gravados, erro, id_ingestao),
    )


def gravar_dataframes(conexao, quadros):
    """Grava usando a transação dos dados e do histórico aberta pela pipeline."""
    if conexao.info.transaction_status != TransactionStatus.INTRANS:
        raise RuntimeError("A gravação requer uma transação aberta pela pipeline.")
    alunos = quadros["alunos"]
    cursos = quadros["cursos"]
    matriculas = quadros["matriculas"]
    with conexao.cursor() as cursor:
        cursor.executemany(
            """insert into public.cursos (nome) values (%s)
               on conflict (nome) do nothing""",
            cursos[["nome"]].itertuples(index=False, name=None),
        )
        cursor.executemany(
            """insert into public.alunos (codigo_origem, nome, email)
               values (%s, %s, %s)
               on conflict (codigo_origem) do update
               set nome = excluded.nome, email = excluded.email
               where alunos.nome is distinct from excluded.nome
                  or alunos.email is distinct from excluded.email""",
            alunos[["codigo_origem", "nome", "email"]].itertuples(index=False, name=None),
        )

    # Resolve as referências textuais dos DataFrames para as chaves do banco.
    mapa_alunos = pd.DataFrame.from_records(
        conexao.execute(
            "select codigo_origem, id_aluno from public.alunos where codigo_origem = any(%s)",
            (alunos["codigo_origem"].tolist(),),
        ).fetchall(), columns=["aluno_codigo_origem", "id_aluno"],
    )
    mapa_cursos = pd.DataFrame.from_records(
        conexao.execute(
            "select nome, id_curso from public.cursos where nome = any(%s)",
            (cursos["nome"].tolist(),),
        ).fetchall(), columns=["curso_nome", "id_curso"],
    )
    vinculos = matriculas.merge(
        mapa_alunos, on="aluno_codigo_origem", how="left", validate="many_to_one"
    ).merge(mapa_cursos, on="curso_nome", how="left", validate="many_to_one")
    if vinculos[["id_aluno", "id_curso"]].isna().any().any():
        raise ValueError("Não foi possível resolver as referências das matrículas.")
    with conexao.cursor() as cursor:
        cursor.executemany(
            """insert into public.matriculas (numero_matricula, id_aluno, id_curso)
               values (%s, %s, %s)
               on conflict (id_aluno, id_curso) do nothing""",
            ((numero, int(aluno), int(curso)) for numero, aluno, curso in
             vinculos[["numero_matricula", "id_aluno", "id_curso"]].itertuples(index=False, name=None)),
        )
    # Quantidade de alunos confirmados, incluindo os que já existiam.
    return len(alunos)

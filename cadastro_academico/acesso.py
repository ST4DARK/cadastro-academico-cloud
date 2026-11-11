"""Provisionamento e comprovação dos perfis de acesso do projeto."""

import os
import secrets

from dotenv import dotenv_values, set_key
from psycopg import sql
from psycopg.errors import InsufficientPrivilege

from .banco import conectar, obter_parametros_conexao
from .configuracao import ARQUIVO_AMBIENTE, PERFIS_BANCO, RAIZ_PROJETO
from .evidencias import salvar_evidencia

def configurar_contas():
    """Aplica os privilégios e provisiona as contas e suas credenciais."""
    ambiente = dotenv_values(ARQUIVO_AMBIENTE, interpolate=False)
    with conectar(somente_leitura=False, perfil="administrador") as conexao:
        conexao.execute((RAIZ_PROJETO / "supabase/migrations/20261111000100_controle_acesso.sql").read_text(encoding="utf-8"))
        parametros = obter_parametros_conexao(perfil="administrador")
        usuario = parametros["user"]
        sufixo = "." + usuario.split(".", 1)[1] if ".pooler.supabase.com" in parametros["host"] else ""
        for perfil, (conta, grupo, prefixo) in PERFIS_BANCO.items():
            senha = ambiente.get(f"{prefixo}_PASSWORD") or secrets.token_urlsafe(32)
            existe = conexao.execute("select 1 from pg_roles where rolname=%s", (conta,)).fetchone()
            with conexao.transaction():
                if not existe:
                    conexao.execute(sql.SQL("create role {} login inherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls password {}").format(sql.Identifier(conta), sql.Literal(senha)))
                else:
                    conexao.execute(sql.SQL("alter role {} password {}").format(sql.Identifier(conta), sql.Literal(senha)))
                conexao.execute(sql.SQL("grant {} to {}").format(sql.Identifier(grupo), sql.Identifier(conta)))
            for chave, valor in ((f"{prefixo}_USER", conta + sufixo), (f"{prefixo}_PASSWORD", senha)):
                set_key(ARQUIVO_AMBIENTE, chave, valor, quote_mode="always")
                os.environ[chave] = valor
            print(f"Perfil {perfil} provisionado; credencial salva somente no .env.")

    if not ambiente.get("RESTORE_DB_PASSWORD"):
        senha_local = secrets.token_urlsafe(32)
        set_key(ARQUIVO_AMBIENTE, "RESTORE_DB_PASSWORD", senha_local, quote_mode="always")
        os.environ["RESTORE_DB_PASSWORD"] = senha_local


def verificar_acessos():
    evidencias = []
    for perfil in PERFIS_BANCO:
        with conectar(somente_leitura=False, perfil=perfil) as conexao:
            usuario = conexao.execute("select current_user").fetchone()[0]
            alunos = conexao.execute("select count(*) from public.alunos").fetchone()[0]
            resultado = {"perfil": perfil, "usuario": usuario, "alunos_visiveis": alunos}
            for operacao, comando in (
                ("atualizar_aluno", "update public.alunos set nome=nome where id_aluno=(select min(id_aluno) from public.alunos)"),
                ("excluir_aluno", "delete from public.alunos where false"),
                ("criar_tabela", "create table public.__verificacao_acesso_negado (id integer)"),
            ):
                try:
                    with conexao.transaction(force_rollback=True):
                        conexao.execute(comando)
                    permitido = True
                except InsufficientPrivilege:
                    permitido = False
                resultado[operacao] = permitido
            esperado_atualizar = perfil in ("operador", "pipeline")
            if resultado["atualizar_aluno"] != esperado_atualizar or resultado["excluir_aluno"] or resultado["criar_tabela"]:
                raise RuntimeError(f"Permissões inesperadas no perfil {perfil}.")
            evidencias.append(resultado)
            print(f"Perfil {perfil}: leitura validada; alteração={resultado['atualizar_aluno']}; exclusão e DDL bloqueados.")
    salvar_evidencia("controle_acesso", evidencias)
    return evidencias

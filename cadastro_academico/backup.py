"""Backup consistente da aplicação e restauração em PostgreSQL local isolado."""

import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql
from dotenv import load_dotenv

from .banco import conectar, obter_parametros_conexao
from .configuracao import ARQUIVO_AMBIENTE, PERFIS_BANCO, RAIZ_PROJETO
from .evidencias import salvar_evidencia

LOGGER = logging.getLogger(__name__)
PASTA_BACKUPS = RAIZ_PROJETO / "backups"
TABELAS = {"alunos": "id_aluno", "cursos": "id_curso", "matriculas": "id_matricula", "ingestoes": "id_ingestao"}
GRUPOS = tuple(grupo for _, grupo, _ in PERFIS_BANCO.values()) + ("anon", "authenticated")


def _json(valor):
    return valor.isoformat() if hasattr(valor, "isoformat") else str(valor)


def resumir_tabelas(conexao):
    conexao.execute("set local time zone 'UTC'")
    resultado = {}
    for tabela, chave in TABELAS.items():
        cursor = conexao.execute(sql.SQL("select * from public.{} order by {}").format(sql.Identifier(tabela), sql.Identifier(chave)))
        colunas = [coluna.name for coluna in cursor.description]
        registros = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
        conteudo = json.dumps(registros, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json).encode()
        resultado[tabela] = {"registros": len(registros), "sha256": hashlib.sha256(conteudo).hexdigest()}
    return resultado


def _ambiente_pg(parametros, sslmode):
    ambiente = os.environ.copy()
    for chave, valor in {"PGHOST": parametros["host"], "PGPORT": parametros.get("port", 5432),
                         "PGDATABASE": parametros.get("dbname", "postgres"), "PGUSER": parametros["user"],
                         "PGPASSWORD": parametros["password"], "PGSSLMODE": sslmode,
                         "PGOPTIONS": "-c statement_timeout=0"}.items():
        ambiente[chave] = str(valor)
    return ambiente


def _executar_ferramenta(comando, ambiente):
    resultado = subprocess.run(comando, env=ambiente, capture_output=True, timeout=180)
    if resultado.returncode:
        # A saída pode conter detalhes de conexão; não é registrada.
        raise RuntimeError(f"{comando[0]} falhou com código {resultado.returncode}.")


def criar_backup():
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    momento = datetime.now(ZoneInfo("America/Sao_Paulo"))
    arquivo = PASTA_BACKUPS / f"academico_{momento:%Y%m%d_%H%M%S}_{uuid4().hex[:8]}.dump"
    temporario = arquivo.with_suffix(".partial")
    try:
        with conectar(somente_leitura=True, perfil="administrador") as conexao:
            parametros = obter_parametros_conexao(perfil="administrador")
            with conexao.transaction():
                conexao.execute("set transaction isolation level repeatable read read only")
                snapshot = conexao.execute("select pg_export_snapshot()").fetchone()[0]
                tabelas = resumir_tabelas(conexao)
                _executar_ferramenta([
                    "pg_dump", "--format=custom", "--schema=public", "--no-owner", "--no-privileges",
                    f"--snapshot={snapshot}", f"--file={temporario}",
                ], _ambiente_pg(parametros, "require"))
        temporario.replace(arquivo)
    except Exception:
        temporario.unlink(missing_ok=True)
        raise
    manifesto = {"arquivo": arquivo.name, "dt_criacao": momento.isoformat(),
                 "escopo": "schema public da aplicação; sem senhas e sem roles globais",
                 "sha256_arquivo": hashlib.sha256(arquivo.read_bytes()).hexdigest(), "tabelas": tabelas}
    arquivo.with_suffix(".manifest.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    salvar_evidencia("backup", manifesto)
    LOGGER.info("Backup consistente criado: %s; tabelas=%s.", arquivo.name, list(tabelas))
    return arquivo.name


def _parametros_local(banco="postgres"):
    load_dotenv(ARQUIVO_AMBIENTE, interpolate=False)
    senha = os.getenv("RESTORE_DB_PASSWORD")
    if not senha:
        raise ValueError("RESTORE_DB_PASSWORD não configurada.")
    # Destino fixo da rede Docker: nunca usa a conexão do Supabase.
    return {"host": "postgres-restauracao", "port": 5432, "dbname": banco, "user": "postgres", "password": senha}


def restaurar_e_validar(nome_arquivo):
    if Path(nome_arquivo).name != nome_arquivo:
        raise ValueError("Use somente o nome do arquivo de backup.")
    arquivo = (PASTA_BACKUPS / nome_arquivo).resolve()
    if not arquivo.is_relative_to(PASTA_BACKUPS.resolve()) or arquivo.suffix != ".dump":
        raise ValueError("Backup fora do diretório permitido.")
    manifesto = json.loads(arquivo.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(arquivo.read_bytes()).hexdigest() != manifesto["sha256_arquivo"]:
        raise ValueError("O arquivo de backup não corresponde ao hash do manifesto.")
    banco = "recuperacao_" + uuid4().hex[:16]
    with psycopg.connect(**_parametros_local(), autocommit=True, connect_timeout=10) as local:
        for grupo in GRUPOS:
            if not local.execute("select 1 from pg_roles where rolname=%s", (grupo,)).fetchone():
                local.execute(sql.SQL("create role {} nologin").format(sql.Identifier(grupo)))
        local.execute(sql.SQL("create database {}").format(sql.Identifier(banco)))
    _executar_ferramenta([
        "pg_restore", "--exit-on-error", "--clean", "--if-exists", "--no-owner", "--no-privileges",
        f"--dbname={banco}", str(arquivo),
    ], _ambiente_pg(_parametros_local(banco), "disable"))
    with psycopg.connect(**_parametros_local(banco), autocommit=True) as local:
        # Reaplica os privilégios versionados; as senhas de usuários não fazem parte do dump.
        migracao = RAIZ_PROJETO / "supabase/migrations/20261111000100_controle_acesso.sql"
        local.execute(migracao.read_text(encoding="utf-8"))
        with local.transaction():
            restauradas = resumir_tabelas(local)
        estrutura = local.execute("""select count(*) filter (where relrowsecurity) from pg_class c
            join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'
            and c.relname in ('alunos','cursos','matriculas','ingestoes')""").fetchone()[0]
    if restauradas != manifesto["tabelas"] or estrutura != 4:
        raise RuntimeError("A restauração diverge dos dados ou do RLS esperados.")
    evidencia = {"arquivo": arquivo.name, "destino": "PostgreSQL 17 local em Docker",
                 "banco_restaurado": banco, "resultado": "aprovado", "rls_ativo_tabelas": estrutura,
                 "tabelas_restauradas": restauradas, "hashes_identicos": True,
                 "dt_validacao": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()}
    salvar_evidencia("restauracao", evidencia)
    LOGGER.info("Restauração aprovada; banco local=%s; hashes das quatro tabelas idênticos.", banco)
    return banco

"""Conexões PostgreSQL por perfil de acesso."""

import os

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict

from .configuracao import ARQUIVO_AMBIENTE, PERFIS_BANCO


def obter_parametros_conexao(perfil="pipeline"):
    load_dotenv(ARQUIVO_AMBIENTE, interpolate=False)
    if perfil != "administrador" and perfil not in PERFIS_BANCO:
        raise ValueError("Perfil de conexão desconhecido.")

    url = os.getenv("DATABASE_URL", "").strip()
    parametros = conninfo_to_dict(url) if url else {
        "host": os.getenv("SUPABASE_DB_HOST", "").strip(),
        "port": os.getenv("SUPABASE_DB_PORT", "5432"),
        "dbname": os.getenv("SUPABASE_DB_NAME", "").strip(),
        "user": os.getenv("SUPABASE_DB_USER", "").strip(),
        "password": os.getenv("SUPABASE_DB_PASSWORD", ""),
    }
    if perfil != "administrador":
        prefixo = PERFIS_BANCO[perfil][2]
        parametros.update(
            user=os.getenv(f"{prefixo}_USER", "").strip(),
            password=os.getenv(f"{prefixo}_PASSWORD", ""),
        )
    faltantes = [campo for campo in ("host", "dbname", "user", "password") if not parametros.get(campo)]
    if faltantes:
        raise ValueError(f"Configuração incompleta do perfil {perfil}: {', '.join(faltantes)}.")
    try:
        parametros["port"] = int(parametros.get("port", 5432))
        if not 1 <= parametros["port"] <= 65535:
            raise ValueError
    except (TypeError, ValueError) as erro:
        raise ValueError("A porta PostgreSQL deve ser um número entre 1 e 65535.") from erro
    return parametros


def conectar(somente_leitura=True, perfil="pipeline"):
    parametros = obter_parametros_conexao(perfil)
    modo = "on" if somente_leitura else "off"
    parametros.update(
        sslmode="require", connect_timeout=10,
        options=f"-c default_transaction_read_only={modo} -c statement_timeout=30000",
    )
    return psycopg.connect(**parametros, autocommit=True)

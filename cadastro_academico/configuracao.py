"""Configuração da coleta e caminhos relativos à raiz do projeto."""

from pathlib import Path
from urllib.parse import urlencode

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
ARQUIVO_AMBIENTE = RAIZ_PROJETO / ".env"
VERSAO_API = "1.4"
QUANTIDADE = 50
CURSOS = ("Informática", "Administração", "Engenharia de Software")
PARAMETROS = {
    "results": QUANTIDADE,
    "nat": "br",
    "seed": "cadastro-academico-cloud",
    "page": 1,
    "inc": "name,email,nat,login",
}
URL_RANDOM_USER = f"https://randomuser.me/api/{VERSAO_API}/?" + urlencode(PARAMETROS)

# Conta LOGIN, grupo de permissões e prefixo das credenciais locais.
PERFIS_BANCO = {
    "leitor": ("academico_consulta", "academico_leitor", "LEITOR_DB"),
    "operador": ("academico_cadastro", "academico_operador", "OPERADOR_DB"),
    "pipeline": ("academico_ingestor", "academico_pipeline", "PIPELINE_DB"),
}

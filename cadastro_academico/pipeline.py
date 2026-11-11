"""Pipeline API → DataFrames → Supabase, com logs e histórico de execução."""

import logging
import traceback

from .banco import conectar
from .configuracao import PARAMETROS, VERSAO_API
from .fonte import buscar_perfis
from .gravacao import finalizar_ingestao, gravar_dataframes, iniciar_ingestao
from .quadros import criar_dataframes
from .transformacao import transformar

LOGGER = logging.getLogger(__name__)


def registrar_erro(etapa, erro, id_ingestao=None):
    """Registra a pilha sem imprimir credenciais, registros ou a mensagem bruta."""
    resumo = f"etapa={etapa}; erro={type(erro).__name__}"
    codigo_sql = getattr(erro, "sqlstate", None)
    if codigo_sql:
        resumo += f"; SQLSTATE={codigo_sql}"
    pilha = "".join(traceback.format_tb(erro.__traceback__)) or "Pilha indisponível."
    LOGGER.error("Ingestão=%s; %s\nPilha de execução:\n%s", id_ingestao, resumo, pilha)
    return resumo


def executar_pipeline():
    id_ingestao = None
    recebidos = 0
    etapa = "conectar"
    try:
        LOGGER.info("Iniciando a pipeline acadêmica.")
        with conectar(somente_leitura=False) as conexao:
            etapa = "iniciar_ingestao"
            id_ingestao = iniciar_ingestao(conexao, {"versao_api": VERSAO_API, **PARAMETROS})
            LOGGER.info("Ingestão=%s iniciada.", id_ingestao)
            try:
                etapa = "extrair"
                resposta = buscar_perfis()
                if isinstance(resposta, dict) and isinstance(resposta.get("results"), list):
                    recebidos = len(resposta["results"])
                LOGGER.info("Ingestão=%s; recebidos=%s perfis.", id_ingestao, recebidos)

                etapa = "transformar"
                dados = transformar(resposta)
                etapa = "criar_dataframes"
                quadros = criar_dataframes(dados)
                for nome, quadro in quadros.items():
                    LOGGER.info("Ingestão=%s; DataFrame=%s; linhas=%s; colunas=%s.",
                                id_ingestao, nome, quadro.shape[0], quadro.shape[1])

                # A pipeline é responsável pela transação dos dados e do histórico.
                etapa = "gravar"
                with conexao.transaction():
                    gravados = gravar_dataframes(conexao, quadros)
                    etapa = "concluir_ingestao"
                    finalizar_ingestao(conexao, id_ingestao, recebidos, gravados)
                    etapa = "confirmar_transacao"
            except Exception as erro:
                resumo = registrar_erro(etapa, erro, id_ingestao)
                try:
                    finalizar_ingestao(conexao, id_ingestao, recebidos, erro=resumo)
                except Exception as erro_historico:
                    registrar_erro("registrar_falha", erro_historico, id_ingestao)
                return 1
        LOGGER.info("Ingestão=%s concluída; alunos_processados=%s.", id_ingestao, gravados)
        return 0
    except Exception as erro:
        registrar_erro(etapa, erro, id_ingestao)
        return 1

"""Evidências sanitizadas para o relatório acadêmico."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from .configuracao import RAIZ_PROJETO

ARQUIVO = RAIZ_PROJETO / "entrega" / "evidencias.json"


def salvar_evidencia(secao, dados):
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    atual = json.loads(ARQUIVO.read_text(encoding="utf-8")) if ARQUIVO.exists() else {}
    atual[secao] = dados
    atual["dt_atualizacao"] = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()
    temporario = ARQUIVO.with_suffix(".tmp")
    temporario.write_text(json.dumps(atual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporario.replace(ARQUIVO)

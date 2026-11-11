"""Acesso à API pública Random User."""

import json
from urllib.request import Request, urlopen

from .configuracao import URL_RANDOM_USER


def buscar_perfis():
    requisicao = Request(
        URL_RANDOM_USER, headers={"User-Agent": "CadastroAcademicoCloud/1.0"}
    )
    with urlopen(requisicao, timeout=30) as resposta:
        return json.load(resposta)

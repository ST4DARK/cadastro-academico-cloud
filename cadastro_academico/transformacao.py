"""Validação dos perfis e simulação dos vínculos acadêmicos."""

from uuid import UUID, NAMESPACE_URL, uuid5

from .configuracao import CURSOS, QUANTIDADE


def transformar(resposta):
    if not isinstance(resposta, dict) or "error" in resposta:
        raise ValueError("A API retornou uma resposta inválida ou um erro.")
    pessoas = resposta.get("results")
    if not isinstance(pessoas, list) or len(pessoas) != QUANTIDADE:
        raise ValueError(f"Esperados {QUANTIDADE} perfis na resposta.")

    alunos = []
    matriculas = []
    for indice, pessoa in enumerate(pessoas, start=1):
        if not isinstance(pessoa, dict) or pessoa.get("nat") != "BR":
            raise ValueError(f"Perfil {indice}: nacionalidade ou formato inválido.")
        login = pessoa.get("login")
        if not isinstance(login, dict) or not isinstance(login.get("uuid"), str):
            raise ValueError(f"Perfil {indice}: UUID de origem ausente.")
        try:
            identificador = UUID(login["uuid"])
        except ValueError as erro:
            raise ValueError(f"Perfil {indice}: UUID de origem inválido.") from erro
        codigo_origem = f"randomuser:{identificador}"
        # O curso e a matrícula permanecem iguais se a resposta mudar de ordem.
        curso = CURSOS[identificador.int % len(CURSOS)]
        numero_matricula = "MAT-" + str(uuid5(NAMESPACE_URL, f"{codigo_origem}:{curso}"))
        nome = pessoa.get("name")
        if not isinstance(nome, dict):
            raise ValueError(f"Perfil {indice}: nome ausente.")
        partes = [nome.get("first"), nome.get("last")]
        if any(not isinstance(parte, str) or not parte.strip() for parte in partes):
            raise ValueError(f"Perfil {indice}: nome incompleto.")
        email = pessoa.get("email")
        if not isinstance(email, str):
            raise ValueError(f"Perfil {indice}: e-mail ausente.")
        email = email.strip().lower()
        if email.count("@") != 1 or any(c.isspace() for c in email):
            raise ValueError(f"Perfil {indice}: formato de e-mail inválido.")
        usuario, dominio = email.split("@")
        if not usuario or "." not in dominio or dominio.startswith(".") or dominio.endswith("."):
            raise ValueError(f"Perfil {indice}: formato de e-mail inválido.")
        alunos.append({
            "codigo_origem": codigo_origem,
            "nome": " ".join(parte.strip() for parte in partes),
            "email": email,
        })
        matriculas.append({
            "numero_matricula": numero_matricula,
            "aluno_codigo_origem": codigo_origem,
            "curso_nome": curso,
        })
    return {
        "alunos": alunos,
        "cursos": [{"nome": curso} for curso in CURSOS],
        "matriculas": matriculas,
    }

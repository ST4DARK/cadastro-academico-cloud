"""Captura evidências locais do Airflow usando uma sessão temporária do Edge."""

import json
import shutil
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "entrega" / "evidencias"


def capturar():
    docker = shutil.which("docker") or r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    resultado = subprocess.run([
        docker, "compose", "exec", "-T", "airflow", "python", "-c",
        "import json; print(json.load(open('/opt/airflow/simple_auth_manager_passwords.json.generated'))['admin'])",
    ], cwd=RAIZ, capture_output=True, text=True, check=True)
    senha = resultado.stdout.strip()
    requisicao = Request("http://localhost:8080/auth/token", data=json.dumps({"username": "admin", "password": senha}).encode(), headers={"Content-Type": "application/json"})
    with urlopen(requisicao, timeout=15) as resposta:
        token = json.load(resposta)["access_token"]
    PASTA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="msedge", headless=True)
        contexto = navegador.new_context(viewport={"width": 1440, "height": 960}, locale="pt-BR")
        contexto.add_cookies([{"name": "_token", "value": token, "url": "http://localhost:8080", "httpOnly": True, "sameSite": "Lax"}])
        pagina = contexto.new_page()
        for dag, arquivo in (("cadastro_academico_supabase", "airflow_ingestao.png"), ("backup_academico_supabase", "airflow_backup.png")):
            pagina.goto("http://localhost:8080/dags/" + dag, wait_until="domcontentloaded")
            pagina.get_by_text(dag, exact=True).first.wait_for(state="visible", timeout=30000)
            try:
                pagina.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeout:
                pass
            if "/auth/" in pagina.url:
                raise RuntimeError("O painel não aceitou a sessão temporária.")
            pagina.screenshot(path=str(PASTA / arquivo), full_page=True)
            print("Captura salva:", arquivo)
        contexto.close()
        navegador.close()


if __name__ == "__main__":
    capturar()

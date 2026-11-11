"""Gera Word e PDF a partir das evidências reais da atividade."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "entrega"
TITULO = "Cadastro Acadêmico Cloud"
SUBTITULO = "Banco de dados em nuvem com controle de acesso, ingestão e recuperação de dados"
CAPA = [
    "Instituição: Anhanguera",
    "Disciplina: Computação em Nuvem",
    "Integrante informado: Marcus",
    "Demais integrantes: __________________________________________",
    "Professor(a): ________________________________________________",
    "Turma/unidade: _______________________________________________",
    "Data: 11 de novembro de 2026",
]


def modelo(e):
    b, r = e["backup"], e["restauracao"]
    assert r["resultado"] == "aprovado" and r["hashes_identicos"]
    assert all(e["airflow"][dag]["state"] == "success" for dag in ("ingestao", "backup"))
    blocos = []
    def h(t): blocos.append(("h", t))
    def p(t): blocos.append(("p", t))
    def tabela(c, linhas): blocos.append(("t", c, linhas))
    def pagina(): blocos.append(("quebra",))

    h("1. Objetivo e atendimento à atividade")
    p("O objetivo foi implementar um banco de dados remoto para cadastro de alunos, com controle de acesso e cópia de segurança. Como ampliação, foi desenvolvida uma pipeline de dados em Python, orquestrada pelo Apache Airflow.")
    p("O banco PostgreSQL está hospedado no Supabase. A orquestração funciona localmente em containers Linux no Docker Desktop com WSL2. Portanto, os dados acadêmicos estão na nuvem, enquanto o painel e o executor do Airflow estão no computador de desenvolvimento.")
    tabela(["Requisito", "Implementação", "Evidência"], [
        ["Banco remoto", "Supabase/PostgreSQL", "Tabelas consultadas pela conexão remota"],
        ["Cadastro", "Alunos, cursos e matrículas", "50 alunos e 50 vínculos persistidos"],
        ["Controle de acesso", "Roles PostgreSQL e políticas RLS", "Logins reais com operações permitidas e negadas"],
        ["Cópia de segurança", "pg_dump em formato custom", "Arquivo e manifesto SHA-256 gerados"],
        ["Recuperação", "pg_restore em banco local separado", "Contagens e hashes idênticos nas quatro tabelas"],
    ])
    h("2. Arquitetura e implementação")
    p("Fluxo: Airflow -> API Random User -> validação -> DataFrames pandas -> transação PostgreSQL -> histórico da execução.")
    p("A API Random User fornece perfis fictícios brasileiros. A versão 1.4, a seed, a página e a quantidade de 50 perfis são fixas. O UUID do perfil identifica o aluno; curso e matrícula são simulados de forma determinística. Esses dados não representam alunos reais da instituição.")
    tabela(["Componente", "Responsabilidade"], [
        ["fonte.py / transformacao.py", "Extrair os perfis e validar os dados"],
        ["quadros.py", "Criar DataFrames e validar referências e duplicações"],
        ["gravacao.py / pipeline.py", "Resolver IDs, gravar o lote e registrar a execução"],
        ["banco.py / acesso.py", "Separar conexões e comprovar os perfis de acesso"],
        ["backup.py", "Exportar, restaurar e comparar os dados"],
        ["dags/", "Orquestrar ingestão e backup com novas tentativas"],
    ])
    tabela(["Tabela", "Chave", "Finalidade"], [
        ["alunos", "id_aluno", "Código de origem, nome, e-mail e datas"],
        ["cursos", "id_curso", "Nome do curso e datas"],
        ["matriculas", "id_matricula", "Vínculo aluno/curso, número, status e datas"],
        ["ingestoes", "id_ingestao", "Parâmetros, status, contagens, horários e erro"],
    ])
    p("A carga usa UPSERT e preserva IDs. A repetição não duplica alunos ou vínculos, nem reativa matrículas canceladas. Alunos e cursos são gravados antes da resolução das chaves das matrículas. Os dados e a conclusão do histórico são confirmados na mesma transação; uma falha desfaz o lote.")
    pagina()
    h("3. Controle de acesso e comprovação")
    p("Foram criados os grupos academico_leitor, academico_operador e academico_pipeline, vinculados a três contas com LOGIN. As senhas foram geradas aleatoriamente e ficam somente no .env local. A ingestão passou a utilizar sua própria conta restrita, em vez da conta administrativa.")
    p("O leitor consulta as quatro tabelas; o operador pode cadastrar e alterar dados acadêmicos e consultar o histórico; a pipeline recebe as permissões necessárias à carga e ao histórico. Nenhum desses perfis pode excluir dados ou criar tabelas. As políticas permitem a leitura dos dados da aplicação aos perfis autorizados; não há segregação individual por aluno nesta versão.")
    tabela(["Perfil", "Alunos visíveis", "Alterar aluno", "Excluir / criar tabela"], [
        [x["perfil"], str(x["alunos_visiveis"]), "Permitido" if x["atualizar_aluno"] else "Bloqueado", "Bloqueado / bloqueado"]
        for x in e["controle_acesso"]
    ])
    p("As verificações usaram conexões reais com as contas academico_consulta, academico_cadastro e academico_ingestor. A alteração permitida foi executada em transação desfeita ao final. As tentativas de exclusão e DDL retornaram falta de privilégio. As contas não são superusuárias, não criam roles ou bancos e não ignoram o RLS.")
    p(f"Foram confirmadas {e['seguranca']['quantidade_politicas']} políticas e RLS ativo nas quatro tabelas. Os papéis anon e authenticated permanecem sem acesso. O controle apresentado é de usuários do PostgreSQL; não foi implementada uma aplicação de cadastro com Supabase Auth. O login admin do Airflow protege apenas o painel de orquestração.")
    h("3.1 Logs e rastreabilidade")
    p("Os logs INFO registram etapas e contagens. Os logs ERROR identificam a etapa, a ingestão, a classe do erro, o SQLSTATE quando disponível e a pilha de execução. A mensagem bruta da exceção e os conteúdos dos perfis não são registrados. O histórico de falhas também fica em ingestoes.mensagem_erro quando o banco está acessível.")
    pagina()
    h("4. Backup e teste de restauração")
    p("A rotina gera um backup lógico do schema public da aplicação, incluindo as quatro tabelas, funções, restrições e políticas. Um snapshot exportado em transação REPEATABLE READ mantém o pg_dump e a comparação de origem no mesmo estado dos dados.")
    p("O arquivo custom é gravado no computador em backups/, fora do Git. Um manifesto registra a data, o hash SHA-256 do arquivo e a quantidade e hash dos registros de cada tabela. As credenciais e roles globais com senhas não fazem parte do dump; os privilégios são reaplicados pela migração versionada.")
    p("A recuperação foi feita com pg_restore em um banco novo no serviço Docker postgres-restauracao, separado do Supabase e sem porta publicada no host. Os perfis de plataforma necessários foram criados localmente sem LOGIN, e a migração de privilégios foi reaplicada. A origem não foi usada como destino de restauração.")
    tabela(["Tabela", "No backup", "Restaurado", "Comparação SHA-256"], [
        [nome, str(val["registros"]), str(r["tabelas_restauradas"][nome]["registros"]), "Idêntico"]
        for nome, val in b["tabelas"].items()
    ])
    p(f"Resultado final: APROVADO. RLS confirmado em {r['rls_ativo_tabelas']} tabelas restauradas. A comparação considerou todas as colunas e linhas, ordenadas pela chave primária e serializadas de forma canônica em UTC.")
    p("Arquivo: " + b["arquivo"])
    p("Banco local recuperado: " + r["banco_restaurado"])
    blocos.append(("codigo", "SHA-256 do arquivo: " + b["sha256_arquivo"]))
    p("Snapshot do backup: " + b["dt_criacao"] + ". Validação: " + r["dt_validacao"] + ".")
    p("O escopo é o banco da aplicação no schema public. Não se trata de uma cópia integral de todos os serviços Supabase, como Auth, Storage e configurações da plataforma. Os arquivos de backup ficam localmente e devem ser preservados em local seguro.")
    pagina()
    h("5. Evidências das execuções")
    tabela(["DAG", "Execução de validação", "Estado final"], [
        [e["airflow"][k]["dag_id"], e["airflow"][k]["run_id"], e["airflow"][k]["state"]]
        for k in ("ingestao", "backup")
    ])
    p("A execução validacao_acesso_001 comprova a ingestão com a conta restrita. A execução validacao_backup_001 comprova as tarefas de exportação e restauração. As DAGs usam acionamento manual; o agendamento periódico pode ser definido conforme a necessidade.")
    for nome, legenda in (("airflow_ingestao.png", "Figura 1. DAG de ingestão no Airflow local."), ("airflow_backup.png", "Figura 2. DAG de backup e restauração no Airflow local.")):
        imagem = PASTA / "evidencias" / nome
        if imagem.exists():
            blocos.append(("imagem", nome, legenda))
    p("As evidências estruturadas estão em entrega/evidencias.json. O manifesto do backup contém os hashes completos de cada tabela para repetição da comparação. As capturas não exibem senhas nem tokens.")
    h("6. Conclusão")
    p("A implementação atende ao cadastro remoto de dados fictícios, ao controle de acesso por perfis e à cópia de segurança com recuperação comprovada. A ingestão e a validação do backup são reproduzíveis pelo Airflow. A restauração foi verificada pela igualdade das contagens e dos hashes das quatro tabelas.")
    p("Antes da entrega, preencher professor, turma/unidade e os demais integrantes na capa. Como evoluções, podem ser adotados agendamento periódico, armazenamento adicional dos backups e uma interface de cadastro para usuários finais.")
    h("7. Referências")
    for referencia in (
        "SUPABASE. PostgreSQL Roles. https://supabase.com/docs/guides/database/postgres/roles",
        "SUPABASE. Database Backups. https://supabase.com/docs/guides/platform/backups",
        "POSTGRESQL. pg_dump. https://www.postgresql.org/docs/current/app-pgdump.html",
        "APACHE AIRFLOW. Quick Start. https://airflow.apache.org/docs/apache-airflow/stable/start.html",
        "RANDOM USER. Documentation. https://randomuser.me/documentation",
    ):
        p(referencia + ". Acesso em: 11 nov. 2026.")
    return blocos


def gerar_word(blocos):
    documento = Document()
    secao = documento.sections[0]
    secao.top_margin = secao.bottom_margin = Cm(2)
    secao.left_margin = secao.right_margin = Cm(2)
    normal = documento.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.12
    for nome in ("Title", "Heading 1", "Heading 2"):
        documento.styles[nome].font.name = "Arial"
        documento.styles[nome].font.color.rgb = RGBColor.from_string("17365D")
    for texto in ("ANHANGUERA", "COMPUTAÇÃO EM NUVEM", TITULO, SUBTITULO):
        p = documento.add_paragraph(texto, "Title" if texto == TITULO else None)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    documento.add_paragraph("")
    for campo in CAPA:
        documento.add_paragraph(campo)
    documento.add_page_break()
    for bloco in blocos:
        tipo = bloco[0]
        if tipo == "h": documento.add_heading(bloco[1], level=1)
        elif tipo in ("p", "codigo"):
            p = documento.add_paragraph(bloco[1])
            if tipo == "codigo":
                for run in p.runs:
                    run.font.name, run.font.size = "Courier New", Pt(8)
        elif tipo == "quebra": documento.add_page_break()
        elif tipo == "t":
            tabela = documento.add_table(rows=1, cols=len(bloco[1]))
            tabela.style = "Light Shading Accent 1"
            for celula, texto in zip(tabela.rows[0].cells, bloco[1]): celula.text = texto
            for linha in bloco[2]:
                for celula, texto in zip(tabela.add_row().cells, linha): celula.text = str(texto)
            documento.add_paragraph("")
        elif tipo == "imagem":
            documento.add_picture(str(PASTA / "evidencias" / bloco[1]), width=Cm(16.5))
            documento.add_paragraph(bloco[2], "Caption")
    rodape = secao.footer.paragraphs[0]
    rodape.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    rodape.add_run("Cadastro Acadêmico Cloud | ")
    campo = OxmlElement("w:fldSimple")
    campo.set(qn("w:instr"), "PAGE")
    rodape._p.append(campo)
    documento.core_properties.title = TITULO
    documento.core_properties.author = "Marcus"
    documento.save(PASTA / "relatorio.docx")


def gerar_pdf(blocos):
    fonte = "Helvetica"
    arial = Path(r"C:\Windows\Fonts\arial.ttf")
    if arial.exists():
        pdfmetrics.registerFont(TTFont("Arial", str(arial)))
        pdfmetrics.registerFont(TTFont("Arial-Bold", str(arial.with_name("arialbd.ttf"))))
        pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")
        fonte = "Arial"
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(name="CorpoProjeto", fontName=fonte, fontSize=10, leading=14, spaceAfter=8))
    estilos.add(ParagraphStyle(name="TituloProjeto", fontName=fonte, fontSize=22, leading=27, textColor=colors.HexColor("#17365D"), alignment=TA_CENTER, spaceAfter=15))
    estilos.add(ParagraphStyle(name="SecaoProjeto", fontName=fonte, fontSize=14, leading=18, textColor=colors.HexColor("#17365D"), spaceBefore=10, spaceAfter=9, keepWithNext=True))
    estilos.add(ParagraphStyle(name="CelulaProjeto", fontName=fonte, fontSize=8, leading=11))
    estilos.add(ParagraphStyle(name="CabecalhoProjeto", fontName=fonte, fontSize=8, leading=11, textColor=colors.white))
    estilos.add(ParagraphStyle(name="CodigoProjeto", fontName="Courier", fontSize=7, leading=10, spaceAfter=8))
    def par(texto, estilo="CorpoProjeto"):
        return Paragraph(escape(str(texto)).replace("\n", "<br/>"), estilos[estilo])
    historia = [Spacer(1, 2*cm), par("ANHANGUERA", "TituloProjeto"), par("COMPUTAÇÃO EM NUVEM", "TituloProjeto"), Spacer(1, cm), par(TITULO, "TituloProjeto"), par(SUBTITULO), Spacer(1, cm)]
    historia += [par(campo) for campo in CAPA]
    historia.append(PageBreak())
    for bloco in blocos:
        tipo = bloco[0]
        if tipo == "h": historia.append(par(bloco[1], "SecaoProjeto"))
        elif tipo == "p": historia.append(par(bloco[1]))
        elif tipo == "codigo": historia.append(par(bloco[1], "CodigoProjeto"))
        elif tipo == "quebra": historia.append(PageBreak())
        elif tipo == "t":
            linhas = [[par(c, "CabecalhoProjeto") for c in bloco[1]]]
            linhas += [[par(c, "CelulaProjeto") for c in linha] for linha in bloco[2]]
            tabela = Table(linhas, colWidths=[(A4[0]-4*cm)/len(bloco[1])]*len(bloco[1]), repeatRows=1, hAlign="LEFT")
            tabela.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17365D")),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F1F5F9")]),
                ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ]))
            historia.extend([tabela, Spacer(1, 0.25*cm)])
        elif tipo == "imagem":
            imagem = Image(str(PASTA / "evidencias" / bloco[1]))
            escala = (A4[0]-4*cm) / imagem.imageWidth
            imagem.drawWidth, imagem.drawHeight = imagem.imageWidth*escala, imagem.imageHeight*escala
            historia.extend([imagem, par(bloco[2])])
    def rodape(canvas, doc):
        canvas.setFont(fonte, 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(2*cm, 1.1*cm, "Cadastro Acadêmico Cloud | Computação em Nuvem")
        canvas.drawRightString(A4[0]-2*cm, 1.1*cm, str(doc.page))
    pdf = SimpleDocTemplate(str(PASTA / "relatorio.pdf"), pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm, title=TITULO, author="Marcus")
    pdf.build(historia, onFirstPage=rodape, onLaterPages=rodape)


def main():
    evidencias = json.loads((PASTA / "evidencias.json").read_text(encoding="utf-8"))
    blocos = modelo(evidencias)
    gerar_word(blocos)
    gerar_pdf(blocos)
    pdf = PdfReader(PASTA / "relatorio.pdf")
    texto = "\n".join(p.extract_text() or "" for p in pdf.pages)
    for obrigatorio in ("Anhanguera", "Marcus", "Controle de acesso", "Backup e teste de restauração"):
        assert obrigatorio.lower() in texto.lower(), f"Texto ausente no PDF: {obrigatorio}"
    word = Document(PASTA / "relatorio.docx")
    assert len(word.tables) >= 5
    print(f"Relatórios gerados e conferidos: PDF ({len(pdf.pages)} páginas), Word.")


if __name__ == "__main__":
    main()

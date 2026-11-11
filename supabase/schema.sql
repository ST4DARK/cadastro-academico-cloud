-- Instalação do zero. Depois aplique a migração de controle de acesso e provisione as contas.
-- Requer que as quatro tabelas ainda não existam. Não apaga dados.
begin;

create table public.alunos (
    id_aluno bigint generated always as identity primary key,
    codigo_origem text not null unique check (codigo_origem !~ '^[[:space:]]*$'),
    nome text not null check (nome !~ '^[[:space:]]*$'),
    email text not null check (email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
    dt_criacao timestamptz not null default now(),
    dt_atualizacao timestamptz not null default now()
);
create unique index alunos_email_unico_idx on public.alunos (lower(email));

create table public.cursos (
    id_curso bigint generated always as identity primary key,
    nome text not null unique check (nome !~ '^[[:space:]]*$'),
    dt_criacao timestamptz not null default now(),
    dt_atualizacao timestamptz not null default now()
);

create table public.matriculas (
    id_matricula bigint generated always as identity primary key,
    numero_matricula text not null unique check (numero_matricula !~ '^[[:space:]]*$'),
    id_aluno bigint not null references public.alunos(id_aluno) on delete restrict,
    id_curso bigint not null references public.cursos(id_curso) on delete restrict,
    status text not null default 'ativa'
        check (status in ('ativa', 'concluida', 'cancelada')),
    dt_criacao timestamptz not null default now(),
    dt_atualizacao timestamptz not null default now(),
    unique (id_aluno, id_curso)
);
create index matriculas_id_curso_idx on public.matriculas(id_curso);

create table public.ingestoes (
    id_ingestao bigint generated always as identity primary key,
    fonte text not null default 'randomuser' check (fonte !~ '^[[:space:]]*$'),
    parametros jsonb not null check (jsonb_typeof(parametros) = 'object'),
    status text not null default 'em_andamento'
        check (status in ('em_andamento', 'concluida', 'falhou')),
    quantidade_registros_recebidos integer not null default 0
        check (quantidade_registros_recebidos >= 0),
    quantidade_registros_gravados integer not null default 0
        check (quantidade_registros_gravados >= 0),
    dt_inicio timestamptz not null default now(),
    dt_fim timestamptz,
    mensagem_erro text,
    check (dt_fim is null or dt_fim >= dt_inicio),
    check (
        (status = 'em_andamento' and dt_fim is null)
        or (status in ('concluida', 'falhou') and dt_fim is not null)
    )
);

create function public.definir_dt_atualizacao()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.dt_atualizacao := statement_timestamp();
    return new;
end;
$$;
revoke execute on function public.definir_dt_atualizacao() from public;

create trigger alunos_definir_dt_atualizacao
before update on public.alunos
for each row execute function public.definir_dt_atualizacao();

create trigger cursos_definir_dt_atualizacao
before update on public.cursos
for each row execute function public.definir_dt_atualizacao();

create trigger matriculas_definir_dt_atualizacao
before update on public.matriculas
for each row execute function public.definir_dt_atualizacao();

insert into public.cursos (nome)
values ('Informática'), ('Administração'), ('Engenharia de Software');

alter table public.alunos enable row level security;
alter table public.cursos enable row level security;
alter table public.matriculas enable row level security;
alter table public.ingestoes enable row level security;

-- Usuários do aplicativo aguardam configuração de permissões.
revoke all on table public.alunos, public.cursos, public.matriculas, public.ingestoes
from anon, authenticated;
revoke all on sequence public.alunos_id_aluno_seq, public.cursos_id_curso_seq,
    public.matriculas_id_matricula_seq, public.ingestoes_id_ingestao_seq from anon, authenticated;

-- Uso administrativo do futuro pipeline, apenas no servidor.
grant select, insert, update on table public.alunos, public.cursos,
    public.matriculas, public.ingestoes to service_role;
grant usage, select on sequence public.alunos_id_aluno_seq, public.cursos_id_curso_seq,
    public.matriculas_id_matricula_seq, public.ingestoes_id_ingestao_seq to service_role;

commit;

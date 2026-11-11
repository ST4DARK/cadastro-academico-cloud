-- Perfis PostgreSQL do projeto. Senhas e contas LOGIN são provisionadas fora deste arquivo.
begin;

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'academico_leitor') then
        create role academico_leitor nologin nosuperuser nocreatedb nocreaterole noreplication nobypassrls;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'academico_operador') then
        create role academico_operador nologin nosuperuser nocreatedb nocreaterole noreplication nobypassrls;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'academico_pipeline') then
        create role academico_pipeline nologin nosuperuser nocreatedb nocreaterole noreplication nobypassrls;
    end if;
end;
$$;

grant usage on schema public to academico_leitor, academico_operador, academico_pipeline;
grant select on public.alunos, public.cursos, public.matriculas, public.ingestoes
    to academico_leitor, academico_operador, academico_pipeline;
grant insert, update on public.alunos, public.cursos, public.matriculas to academico_operador;
grant insert, update on public.alunos, public.ingestoes to academico_pipeline;
grant insert on public.cursos, public.matriculas to academico_pipeline;
grant usage, select on sequence public.alunos_id_aluno_seq, public.cursos_id_curso_seq,
    public.matriculas_id_matricula_seq to academico_operador, academico_pipeline;
grant usage, select on sequence public.ingestoes_id_ingestao_seq to academico_pipeline;
grant execute on function public.definir_dt_atualizacao() to academico_operador, academico_pipeline;

-- Leitura autorizada para os três perfis; a Data API continua bloqueada.
do $$
declare t text;
begin
    foreach t in array array['alunos','cursos','matriculas','ingestoes'] loop
        execute format('drop policy if exists academico_consultar on public.%I', t);
        execute format('create policy academico_consultar on public.%I for select to academico_leitor, academico_operador, academico_pipeline using (true)', t);
        execute format('alter table public.%I enable row level security', t);
        execute format('revoke all on public.%I from anon, authenticated', t);
    end loop;
    foreach t in array array['alunos','cursos','matriculas'] loop
        execute format('drop policy if exists academico_inserir on public.%I', t);
        execute format('create policy academico_inserir on public.%I for insert to academico_operador, academico_pipeline with check (true)', t);
    end loop;
end;
$$;

drop policy if exists academico_atualizar on public.alunos;
create policy academico_atualizar on public.alunos for update
    to academico_operador, academico_pipeline using (true) with check (true);
drop policy if exists academico_atualizar on public.cursos;
create policy academico_atualizar on public.cursos for update
    to academico_operador using (true) with check (true);
drop policy if exists academico_atualizar on public.matriculas;
create policy academico_atualizar on public.matriculas for update
    to academico_operador using (true) with check (true);
drop policy if exists academico_inserir on public.ingestoes;
create policy academico_inserir on public.ingestoes for insert
    to academico_pipeline with check (true);
drop policy if exists academico_atualizar on public.ingestoes;
create policy academico_atualizar on public.ingestoes for update
    to academico_pipeline using (true) with check (true);

commit;

import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';
import { expect, test } from 'vitest';

test('Postgres migration enforces ownership, retention, deletion, and anonymous denial',async()=>{
 const db=new PGlite();
 try {
  await db.exec(`
   create role anon; create role authenticated;
   create schema auth; create table auth.users(id uuid primary key);
   create function auth.uid() returns uuid language sql stable as $$
    select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid
   $$;
   grant usage on schema auth to authenticated, anon;
   grant execute on function auth.uid() to authenticated, anon;
   insert into auth.users values ('11111111-1111-4111-8111-111111111111'),('22222222-2222-4222-8222-222222222222');
  `);
  await db.exec(await readFile(new URL('../../supabase/migrations/202609220001_accounts.sql',import.meta.url),'utf8'));
  const a='11111111-1111-4111-8111-111111111111',b='22222222-2222-4222-8222-222222222222';
  const asUser=async id=>{await db.exec('set role authenticated');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id])};
  const insert=(id,n)=>db.query("insert into public.nova_records(user_id,collection,payload) values ($1,'notes',$2)",[id,{content:'note '+n}]);
  await asUser(a);await insert(a,0);
  await expect(insert(b,0)).rejects.toThrow(/row-level security/);
  await asUser(b);
  expect((await db.query('select * from public.nova_records')).rows).toHaveLength(0);
  await db.query('delete from public.nova_records where user_id=$1',[a]);
  await insert(b,0);
  await asUser(a);
  expect((await db.query('select * from public.nova_records')).rows).toHaveLength(1);
  for(let i=1;i<=102;i++)await insert(a,i);
  const rows=(await db.query('select payload from public.nova_records order by id')).rows;
  expect(rows).toHaveLength(100);expect(rows[0].payload.content).toBe('note 3');
  await expect(db.query("update public.nova_records set user_id=$1",[b])).rejects.toThrow(/permission denied/);
  await db.exec('delete from public.nova_records');
  expect((await db.query('select * from public.nova_records')).rows).toHaveLength(0);
  await asUser(b);expect((await db.query('select * from public.nova_records')).rows).toHaveLength(1);
  await db.exec('set role anon');
  await expect(db.query('select * from public.nova_records')).rejects.toThrow(/permission denied/);
 } finally {await db.close()}
},30000);

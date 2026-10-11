"""Isolamento de acessos, convites e identidade única entre lojas."""
from datetime import timedelta
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.auth import hash_pw, token_for
from app.models import Base, User, AuditLog, _now
from app.organizacoes_audit import AuditOrganizacao
from app.organizacoes_models import Organizacao, VinculoOrganizacao, FornecedorIdentidade, FornecedorVinculo, ConviteFornecedor


@pytest.fixture
def org_api(tmp_path, request):
    engine = create_engine(f"sqlite:///{tmp_path / 'org.db'}", connect_args={'check_same_thread': False, 'timeout': 15})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        users = [User(nome=name, email=f'{name}@teste.local', perfil=role, senha_hash=hash_pw('senha-teste'))
            for name, role in [('a','admin'),('b','admin'),('fornecedor','fornecedor'),('consulta','consulta')]]
        db.add_all(users)
        db.flush()
        db.add_all([Organizacao(id=1,nome='Loja A'),Organizacao(id=2,nome='Loja B')])
        db.flush()
        db.add_all([VinculoOrganizacao(user_id=users[0].id,organizacao_id=1,perfil='admin'),
            VinculoOrganizacao(user_id=users[1].id,organizacao_id=2,perfil='admin'),
            VinculoOrganizacao(user_id=users[3].id,organizacao_id=1,perfil='consulta')])
        db.commit()
        headers = {u.nome:{'Authorization':f'Bearer {token_for(u)}'} for u in users}
        ids = {u.nome:u.id for u in users}
    def isolated_db():
        with sessions() as db:
            yield db
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = isolated_db
    # Cada cenário mantém sua própria origem HTTP sem desabilitar rate limiting.
    client = TestClient(app, client=(request.node.nodeid, 50000))
    try:
        yield client, headers, sessions, ids
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def invite(c,h,org=1,email='fornecedor@teste.local'):
    r = c.post(f'/organizacoes/{org}/convites',headers=h['a' if org==1 else 'b'],json={'email':email,'nome':'Fornecedor'})
    assert r.status_code==201,r.text
    return r.json()


def accept(c,h,inv):
    return c.post('/organizacoes/convites/aceitar',headers=h['fornecedor'],json={'token':inv['token']})


def test_lista_e_admin_da_outra_loja(org_api):
    c,h,_,_=org_api
    assert [x['id'] for x in c.get('/organizacoes',headers=h['a']).json()]==[1]
    for path in ['/organizacoes/2','/organizacoes/2/membros','/organizacoes/2/convites']:
        assert c.get(path,headers=h['a']).status_code==403
    assert c.post('/organizacoes/2/convites',headers=h['a'],json={'email':'x@teste.local','nome':'X'}).status_code==403
    assert c.get('/organizacoes/1/membros',headers=h['consulta']).status_code==403
    assert c.post('/organizacoes',headers=h['b'],json={'nome':'C'}).status_code==403
    r=c.post('/organizacoes',headers=h['a'],json={'nome':'C'})
    assert r.status_code==201
    assert c.get(f"/organizacoes/{r.json()['id']}",headers=h['a']).json()['perfil']=='admin'


def test_mesma_identidade_multiplas_lojas_idempotencia_e_privacidade(org_api):
    c,h,sessions,_=org_api
    a,b=invite(c,h),invite(c,h,2)
    first=accept(c,h,a)
    assert first.status_code==200,first.text
    assert accept(c,h,a).json()==first.json()
    assert accept(c,h,b).json()['fornecedor_identidade_id']==first.json()['fornecedor_identidade_id']
    assert len(c.get('/organizacoes',headers=h['fornecedor']).json())==2
    assert c.get('/organizacoes/1/membros',headers=h['fornecedor']).status_code==403
    listed=c.get('/organizacoes/1/convites',headers=h['a'])
    assert 'token' not in listed.text
    assert listed.headers['cache-control']=='private, no-store'
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(FornecedorIdentidade))==1
        assert db.scalar(select(func.count()).select_from(FornecedorVinculo))==2
        rows=db.scalars(select(ConviteFornecedor)).all()
        assert all(row.token_hash!=a['token'] for row in rows)
        audit=json.dumps([{'antes':x.antes,'depois':x.depois} for x in db.scalars(select(AuditOrganizacao))])
        assert a['token'] not in audit and b['token'] not in audit


def test_expirado_revogado_email_incorreto(org_api):
    c,h,sessions,_=org_api
    expired=invite(c,h)
    with sessions() as db:
        db.get(ConviteFornecedor,expired['id']).expires_at=_now()-timedelta(seconds=1)
        db.commit()
    assert accept(c,h,expired).status_code==409
    revoked=invite(c,h)
    assert c.post(f"/organizacoes/1/convites/{revoked['id']}/revogar",headers=h['a']).status_code==200
    assert accept(c,h,revoked).status_code==409
    wrong=invite(c,h,email='outro@teste.local')
    assert accept(c,h,wrong).status_code==403
    assert c.post(f"/organizacoes/2/convites/{wrong['id']}/revogar",headers=h['b']).status_code==404


def test_cadastro_por_convite_sem_jwt_ou_email_controlavel(org_api):
    c,h,sessions,_=org_api
    inv=invite(c,h,email='novo@teste.local')
    payload={'token':inv['token'],'nome':'Novo','senha':'senha-segura'}
    r=c.post('/organizacoes/convites/registrar',json=payload)
    assert r.status_code==201,r.text
    assert 'senha' not in r.text and 'access_token' not in r.text
    with sessions() as db:
        user=db.scalar(select(User).where(User.email=='novo@teste.local'))
        assert user.perfil=='fornecedor' and user.senha_hash!='senha-segura'
    assert c.post('/organizacoes/convites/registrar',json=payload).status_code==409
    assert c.post('/organizacoes/convites/registrar',json={**payload,'email':'atacante@teste.local'}).status_code==422


def test_existente_exige_login_e_campos_validos(org_api):
    c,h,_,_=org_api
    inv=invite(c,h)
    assert c.post('/organizacoes/convites/registrar',json={'token':inv['token'],'nome':'F','senha':'senha-segura'}).status_code==409
    assert c.post('/organizacoes/1/convites',headers=h['a'],json={'email':'sem-email','nome':'X'}).status_code==422
    assert c.post('/organizacoes',headers=h['a'],json={'nome':'   '}).status_code==422
    assert c.get('/organizacoes').status_code in (401,403)


def test_acesso_financeiro_somente_membro_original(org_api):
    c,h,sessions,ids=org_api
    for who in ('b','fornecedor'):
        for path in ('/pessoas','/notas','/pagamentos','/visao-geral/resumo'):
            assert c.get(path,headers=h[who]).status_code==403
    assert c.get('/notas',headers={**h['a'],'X-Organizacao-Id':'2'}).status_code==403
    with sessions() as db:
        db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id==ids['a'])).ativo=False
        db.commit()
    assert c.get('/notas',headers=h['a']).status_code==403


def test_admin_original_nao_lista_ou_reseta_fornecedor_externo(org_api):
    c,h,_,ids=org_api
    r=c.get('/auth/users',headers=h['a'])
    assert r.status_code==200,r.text
    assert ids['fornecedor'] not in [u['id'] for u in r.json()]
    assert c.patch(f"/auth/users/{ids['fornecedor']}",headers=h['a'],json={'nome':'Troca'}).status_code==404


def test_vinculo_inativo_nao_reativado_por_novo_convite(org_api):
    c,h,sessions,ids=org_api
    inv=invite(c,h)
    assert accept(c,h,inv).status_code==200
    with sessions() as db:
        db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.user_id==ids['fornecedor'])).ativo=False
        db.commit()
    assert accept(c,h,inv).status_code==403
    assert accept(c,h,invite(c,h)).status_code==409


def test_duas_aceitacoes_concorrentes_mesmo_convite(org_api):
    from concurrent.futures import ThreadPoolExecutor
    c,h,sessions,_=org_api
    inv=invite(c,h)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses=list(executor.map(lambda _:accept(c,h,inv),range(2)))
    assert all(r.status_code==200 for r in responses),[r.text for r in responses]
    assert responses[0].json()==responses[1].json()
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(FornecedorIdentidade))==1
        assert db.scalar(select(func.count()).select_from(FornecedorVinculo))==1
        assert db.scalar(select(func.count()).select_from(AuditOrganizacao).where(AuditOrganizacao.acao=='convite_fornecedor_aceito'))==1


def test_convites_concorrentes_lojas_distintas_uma_identidade(org_api):
    from concurrent.futures import ThreadPoolExecutor
    c,h,sessions,_=org_api
    invitations=[invite(c,h),invite(c,h,2)]
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses=list(executor.map(lambda inv:accept(c,h,inv),invitations))
    assert all(r.status_code==200 for r in responses),[r.text for r in responses]
    assert responses[0].json()['fornecedor_identidade_id']==responses[1].json()['fornecedor_identidade_id']
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(FornecedorIdentidade))==1
        assert db.scalar(select(func.count()).select_from(FornecedorVinculo))==2


def test_bootstrap_snapshot_uma_vez_sem_reativar(tmp_path):
    from app.organizacoes_bootstrap import inicializar_organizacao_original
    engine=create_engine(f"sqlite:///{tmp_path/'bootstrap.db'}")
    Base.metadata.create_all(engine)
    sessions=sessionmaker(bind=engine)
    with sessions() as db:
        admin=User(nome='A',email='a@boot.local',perfil='admin',senha_hash='hash')
        supplier=User(nome='F',email='f@boot.local',perfil='fornecedor',senha_hash='hash')
        db.add_all([admin,supplier]);db.commit()
        inicializar_organizacao_original(db)
        assert db.scalar(select(func.count()).select_from(VinculoOrganizacao))==1
        member=db.scalar(select(VinculoOrganizacao));member.ativo=False;db.commit()
        late=User(nome='B',email='b@boot.local',perfil='admin',senha_hash='hash')
        db.add(late);db.commit()
        inicializar_organizacao_original(db)
        assert db.scalar(select(func.count()).select_from(Organizacao))==1
        assert db.scalar(select(func.count()).select_from(VinculoOrganizacao))==1
        assert db.scalar(select(VinculoOrganizacao)).ativo is False
    engine.dispose()


def test_aceitar_e_revogar_concorrentes_exclusivos(org_api):
    from concurrent.futures import ThreadPoolExecutor
    c,h,sessions,_=org_api
    inv=invite(c,h)
    with ThreadPoolExecutor(max_workers=2) as executor:
        accepted=executor.submit(accept,c,h,inv)
        revoked=executor.submit(c.post,f"/organizacoes/1/convites/{inv['id']}/revogar",headers=h['a'])
        statuses=[accepted.result().status_code,revoked.result().status_code]
    assert sorted(statuses)==[200,409],statuses
    with sessions() as db:
        row=db.get(ConviteFornecedor,inv['id'])
        assert bool(row.accepted_at)!=bool(row.revoked_at)
        expected=int(bool(row.accepted_at))
        assert db.scalar(select(func.count()).select_from(FornecedorIdentidade))==expected


def test_registros_concorrentes_nao_duplicam_conta(org_api):
    from concurrent.futures import ThreadPoolExecutor
    c,h,sessions,_=org_api
    inv=invite(c,h,email='concorrente@teste.local')
    payload={'token':inv['token'],'nome':'Concorrente','senha':'senha-concorrente'}
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses=list(executor.map(lambda _:c.post('/organizacoes/convites/registrar',json=payload),range(2)))
    assert sorted(r.status_code for r in responses)==[201,409],[r.text for r in responses]
    assert all(inv['token'] not in r.text and payload['senha'] not in r.text for r in responses)
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.email=='concorrente@teste.local'))==1
        assert db.scalar(select(func.count()).select_from(FornecedorIdentidade))==1


def test_senha_propria_fornecedor_e_reset_externo_bloqueado(org_api):
    c,h,_,ids=org_api
    reset=c.post(f"/auth/users/{ids['fornecedor']}/password",headers=h['a'],json={'senha':'senha-resetada'})
    assert reset.status_code==404,reset.text
    own=c.post('/auth/me/password',headers=h['fornecedor'],json={'senha_atual':'senha-teste','nova':'senha-alterada'})
    assert own.status_code==200,own.text
    assert c.get('/organizacoes',headers=h['fornecedor']).status_code==401
    login=c.post('/auth/login',json={'email':'fornecedor@teste.local','senha':'senha-alterada'})
    assert login.status_code==200,login.text


def test_fornecedor_vinculado_a_lojas_nao_sofre_tomada_conta(org_api):
    c,h,_,ids=org_api
    assert accept(c,h,invite(c,h)).status_code==200
    assert accept(c,h,invite(c,h,2)).status_code==200
    users=c.get('/auth/users',headers=h['a']).json()
    assert ids['fornecedor'] not in [u['id'] for u in users]
    for body in ({'nome':'Troca'}, {'perfil':'admin'}):
        assert c.patch(f"/auth/users/{ids['fornecedor']}",headers=h['a'],json=body).status_code==404
    assert c.post(f"/auth/users/{ids['fornecedor']}/password",headers=h['a'],json={'senha':'senha-invasor'}).status_code==404
    assert c.post('/auth/login',json={'email':'fornecedor@teste.local','senha':'senha-teste'}).status_code==200
    assert c.get('/organizacoes/2',headers=h['fornecedor']).status_code==200


def test_validacao_nao_reflete_segredos(org_api):
    c,h,_,_=org_api
    inv=invite(c,h,email='segredo@teste.local')
    weak='fraca'
    r=c.post('/organizacoes/convites/registrar',json={'token':inv['token'],'nome':'Nome','senha':weak})
    assert r.status_code==422
    assert weak not in r.text and inv['token'] not in r.text
    raw='token-invalido'
    r=c.post('/organizacoes/convites/aceitar',headers=h['fornecedor'],json={'token':raw})
    assert r.status_code==422 and raw not in r.text


def test_auditoria_loja_original_nao_expoe_outra_organizacao(org_api):
    c,h,sessions,_=org_api
    secret_name='Loja confidencial B'
    with sessions() as db:
        db.get(Organizacao,2).nome=secret_name
        db.commit()
    inv=invite(c,h,2)
    assert accept(c,h,inv).status_code==200
    assert c.post('/auth/login',json={'email':'b@teste.local','senha':'senha-teste'},headers={'X-Forwarded-For':'192.0.2.77'}).status_code==200
    for path in ('/auditoria','/export/auditoria.csv'):
        r=c.get(path,headers=h['a'])
        assert r.status_code==200,r.text
        assert 'convite_fornecedor' not in r.text
        assert secret_name not in r.text and '192.0.2.77' not in r.text
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(AuditOrganizacao))>=3

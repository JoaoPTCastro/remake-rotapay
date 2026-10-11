"""Portal autorizado por cadastro local; declarações não confirmam o banco."""
from contextlib import contextmanager
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from ..auth import current_user
from ..database import get_control_db
from ..models import User, Pessoa, PessoaChavePix, Pagamento, NotaObrigacao, NotaAbatimento
from ..organizacoes_models import Organizacao, VinculoOrganizacao, FornecedorIdentidade, FornecedorVinculo
from ..fornecedores_models import CadastroFornecedorOrganizacao, RecebimentoFornecedor
from ..fornecedores_schemas import CadastroFornecedorIn, MembroOrganizacaoIn, AdicionarMembroIn, RecebimentoFornecedorIn
from ..schemas import ChavePixIn
from ..organizacoes import exigir_vinculo
from ..ambientes import abrir_financeiro
from ..audit import audit
from .organizacoes import privado, transacao_segura
from .pessoas import _save_child, _child_out
from .pagamentos import _query as pagamentos_query, _orcamento as orcamento_pagamento

router = APIRouter(prefix='/organizacoes', tags=['portal fornecedor'], dependencies=[Depends(privado)])


def bloquear_organizacao(db, org_id):
    db.execute(update(Organizacao).where(Organizacao.id == org_id).values(nome=Organizacao.nome))
    db.scalar(select(Organizacao).where(Organizacao.id == org_id).with_for_update())


@contextmanager
def financeiro(db, org_id):
    local = db if org_id == 1 else abrir_financeiro(db, org_id)
    try:
        # Somente tabela aditiva local, sem alterar fatos ou chaves existentes.
        from sqlalchemy.schema import CreateTable
        with local.get_bind().begin() as conn:
            conn.execute(CreateTable(RecebimentoFornecedor.__table__, if_not_exists=True))
        yield local
    finally:
        if local is not db:
            local.close()


def identidade_autorizada(db, org_id, user_id):
    alvo = db.get(User, user_id)
    if not alvo or not alvo.ativo:
        raise HTTPException(404, 'Fornecedor não encontrado')
    exigir_vinculo(db, alvo, org_id)
    identidade = db.scalar(select(FornecedorIdentidade).where(FornecedorIdentidade.user_id == user_id))
    vinculo = db.scalar(select(FornecedorVinculo).where(FornecedorVinculo.identidade_id == identidade.id,
        FornecedorVinculo.organizacao_id == org_id, FornecedorVinculo.ativo.is_(True))) if identidade else None
    if not vinculo:
        raise HTTPException(403, 'Vínculo de fornecedor indisponível')
    return identidade


def cadastro_portal(db, org_id, usuario):
    org, _ = exigir_vinculo(db, usuario, org_id)
    identidade = identidade_autorizada(db, org_id, usuario.id)
    cadastro = db.scalar(select(CadastroFornecedorOrganizacao).where(
        CadastroFornecedorOrganizacao.organizacao_id == org_id,
        CadastroFornecedorOrganizacao.identidade_id == identidade.id))
    if not cadastro:
        raise HTTPException(409, 'A loja ainda precisa vincular seu cadastro de fornecedor')
    return org, cadastro


def pessoa_autorizada(local, cadastro):
    pessoa = local.get(Pessoa, cadastro.pessoa_local_id)
    if not pessoa or not pessoa.ativo or pessoa.tipo not in ('fornecedor', 'ambos'):
        raise HTTPException(403, 'Cadastro de fornecedor indisponível')
    return pessoa


def recibo_out(recibo, pagamento):
    if not recibo:
        return None
    return {'id': recibo.id, 'referencia': recibo.referencia, 'observacao': recibo.observacao,
        'created_at': recibo.created_at, 'valor_declarado': recibo.valor_declarado,
        'situacao': 'cancelado' if pagamento.cancelado else (
            'divergente' if round(pagamento.valor, 2) != round(recibo.valor_declarado, 2) else 'declarado')}


@router.get('/{organizacao_id}/fornecedores')
def fornecedores(organizacao_id: int, db: Session = Depends(get_control_db), usuario: User = Depends(current_user)):
    exigir_vinculo(db, usuario, organizacao_id, admin=True)
    rows = db.execute(select(User, FornecedorIdentidade, FornecedorVinculo).join(FornecedorIdentidade,
        FornecedorIdentidade.user_id == User.id).join(FornecedorVinculo,
        FornecedorVinculo.identidade_id == FornecedorIdentidade.id).where(
        FornecedorVinculo.organizacao_id == organizacao_id).order_by(User.id)).all()
    membros_ativos = set(db.scalars(select(VinculoOrganizacao.user_id).where(VinculoOrganizacao.organizacao_id == organizacao_id, VinculoOrganizacao.ativo.is_(True))))
    cadastros = {c.identidade_id: c.pessoa_local_id for c in db.scalars(select(CadastroFornecedorOrganizacao).where(
        CadastroFornecedorOrganizacao.organizacao_id == organizacao_id))}
    with financeiro(db, organizacao_id) as local:
        pessoas = [{'id': p.id, 'nome': p.nome} for p in local.scalars(select(Pessoa).where(
            Pessoa.ativo.is_(True), Pessoa.tipo.in_(('fornecedor', 'ambos'))).order_by(Pessoa.nome))]
    return {'fornecedores': [{'user_id': u.id, 'nome': u.nome, 'email': u.email, 'ativo': v.ativo and u.ativo and u.id in membros_ativos,
        'pessoa_id': cadastros.get(i.id)} for u, i, v in rows], 'cadastros': pessoas}


@router.put('/{organizacao_id}/fornecedores/{user_id}/cadastro')
@transacao_segura
def vincular(organizacao_id: int, user_id: int, body: CadastroFornecedorIn,
             db: Session = Depends(get_control_db), usuario: User = Depends(current_user)):
    bloquear_organizacao(db, organizacao_id)
    exigir_vinculo(db, usuario, organizacao_id, admin=True)
    identidade = identidade_autorizada(db, organizacao_id, user_id)
    existente = db.scalar(select(CadastroFornecedorOrganizacao).where(
        CadastroFornecedorOrganizacao.organizacao_id == organizacao_id,
        CadastroFornecedorOrganizacao.identidade_id == identidade.id))
    if existente:
        if existente.pessoa_local_id != body.pessoa_id:
            raise HTTPException(409, 'Vínculo existente não pode ser transferido para outro cadastro')
        return {'user_id': user_id, 'pessoa_id': existente.pessoa_local_id}
    with financeiro(db, organizacao_id) as local:
        pessoa = local.get(Pessoa, body.pessoa_id)
        if not pessoa or not pessoa.ativo or pessoa.tipo not in ('fornecedor', 'ambos'):
            raise HTTPException(422, 'Selecione um fornecedor ativo desta loja')
    db.add(CadastroFornecedorOrganizacao(organizacao_id=organizacao_id, identidade_id=identidade.id,
        pessoa_local_id=body.pessoa_id, created_by=usuario.id))
    audit(db, usuario.id, 'cadastro_fornecedor_vinculado', 'organizacao', organizacao_id,
        depois={'user_id': user_id, 'pessoa_local_id': body.pessoa_id})
    db.commit()
    return {'user_id': user_id, 'pessoa_id': body.pessoa_id}


@router.get('/{organizacao_id}/portal-fornecedor')
def portal(organizacao_id: int, db: Session = Depends(get_control_db), usuario: User = Depends(current_user)):
    org, cadastro = cadastro_portal(db, organizacao_id, usuario)
    with financeiro(db, organizacao_id) as local:
        pessoa = pessoa_autorizada(local, cadastro)
        rows = pagamentos_query(local).filter(Pagamento.fornecedor_id == pessoa.id,
            Pagamento.tipo.in_(('cliente_fornecedor', 'repasse_fornecedor'))).order_by(Pagamento.data.desc(), Pagamento.id.desc()).all()
        pagamentos = [row[0] for row in rows]
        orcamentos = {row[0].id: orcamento_pagamento(row[0], 'fornecedor', row[2], row[7]) for row in rows}
        recibos = {r.pagamento_id: r for r in local.scalars(select(RecebimentoFornecedor).where(RecebimentoFornecedor.pessoa_id == pessoa.id))}
        notas = list(local.scalars(select(NotaObrigacao).where(NotaObrigacao.pessoa_id == pessoa.id,
            NotaObrigacao.relacao == 'fornecedor').order_by(NotaObrigacao.id.desc())))
        totais_notas = dict(local.execute(select(NotaAbatimento.nota_id, func.sum(NotaAbatimento.valor)).join(NotaObrigacao, NotaObrigacao.id == NotaAbatimento.nota_id).where(NotaObrigacao.pessoa_id == pessoa.id, NotaObrigacao.relacao == 'fornecedor', NotaAbatimento.estornado.is_(False)).group_by(NotaAbatimento.nota_id)).all())
        notas_out = []
        for n in notas:
            saldo = round(n.valor_original - totais_notas.get(n.id, 0), 2)
            notas_out.append({'id': n.id, 'numero_documento': n.numero_documento, 'valor_original': n.valor_original,
                'saldo': saldo, 'vencimento': n.vencimento, 'situacao': 'cancelada' if n.cancelada else ('quitada' if saldo <= 0 else 'aberta')})
        pagamentos_out = [{**{k: getattr(p, k) for k in ('id', 'codigo', 'tipo', 'forma', 'valor', 'data', 'cancelado')},
            'orcamento': orcamentos[p.id], 'recebimento': recibo_out(recibos.get(p.id), p)} for p in pagamentos]
        return {'organizacao_id': org.id, 'organizacao_nome': org.nome, 'fornecedor': {'id': pessoa.id, 'nome': pessoa.nome},
            'pagamentos': pagamentos_out, 'notas': notas_out,
            'chaves_pix': [_child_out(k) for k in local.scalars(select(PessoaChavePix).where(PessoaChavePix.pessoa_id == pessoa.id).order_by(PessoaChavePix.id))],
            'resumo': {'total_recebimentos': round(sum(p.valor for p in pagamentos if not p.cancelado), 2),
                'saldo_notas': round(sum(n['saldo'] for n in notas_out if n['situacao'] != 'cancelada'), 2),
                'saldo_disponivel': round(sum(o['saldo_disponivel'] for o in orcamentos.values()), 2),
                'total_aplicado': round(sum(o['aplicado'] for o in orcamentos.values()), 2),
                'total_declarado': round(sum(p.valor for p in pagamentos if not p.cancelado and p.id in recibos and recibo_out(recibos[p.id], p)['situacao'] == 'declarado'), 2)}}


def salvar_chave(org_id, chave_id, body, db, usuario):
    bloquear_organizacao(db, org_id)
    _, cadastro = cadastro_portal(db, org_id, usuario)
    with financeiro(db, org_id) as local:
        pessoa = pessoa_autorizada(local, cadastro)
        # Reserva local antes de principalidade; protege também escritores internos.
        local.execute(update(Pessoa).where(Pessoa.id == pessoa.id).values(nome=Pessoa.nome, updated_at=Pessoa.updated_at))
        return _save_child(local, usuario, pessoa.id, PessoaChavePix, ChavePixIn, body, chave_id)


@router.post('/{organizacao_id}/portal-fornecedor/chaves-pix', status_code=201)
@transacao_segura
def criar_chave(organizacao_id: int, body: ChavePixIn, db: Session = Depends(get_control_db), usuario: User = Depends(current_user)):
    return salvar_chave(organizacao_id, None, body, db, usuario)


@router.patch('/{organizacao_id}/portal-fornecedor/chaves-pix/{chave_id}')
@transacao_segura
def editar_chave(organizacao_id: int, chave_id: int, body: ChavePixIn, db: Session = Depends(get_control_db), usuario: User = Depends(current_user)):
    return salvar_chave(organizacao_id, chave_id, body, db, usuario)


@router.post('/{organizacao_id}/portal-fornecedor/pagamentos/{pagamento_id}/confirmar-recebimento')
@transacao_segura
def confirmar(organizacao_id: int, pagamento_id: int, body: RecebimentoFornecedorIn,
              db: Session = Depends(get_control_db), usuario: User = Depends(current_user)):
    bloquear_organizacao(db, organizacao_id)
    _, cadastro = cadastro_portal(db, organizacao_id, usuario)
    with financeiro(db, organizacao_id) as local:
        pessoa = pessoa_autorizada(local, cadastro)
        local.execute(update(Pagamento).where(Pagamento.id == pagamento_id).values(version=Pagamento.version, updated_at=Pagamento.updated_at))
        p = local.scalar(select(Pagamento).where(Pagamento.id == pagamento_id).with_for_update())
        if not p or p.fornecedor_id != pessoa.id or p.tipo not in ('cliente_fornecedor', 'repasse_fornecedor'):
            raise HTTPException(404, 'Pagamento não encontrado')
        if p.cancelado:
            raise HTTPException(409, 'Pagamento cancelado não pode ser confirmado')
        recibo = local.scalar(select(RecebimentoFornecedor).where(RecebimentoFornecedor.pagamento_id == p.id))
        if recibo:
            if recibo.referencia != body.referencia or recibo.observacao != body.observacao or round(recibo.valor_declarado, 2) != round(p.valor, 2):
                raise HTTPException(409, 'Recebimento já declarado; histórico preservado')
            return recibo_out(recibo, p)
        recibo = RecebimentoFornecedor(pagamento_id=p.id, pessoa_id=pessoa.id, usuario_central_id=usuario.id,
            valor_declarado=p.valor, pagamento_version=p.version, referencia=body.referencia, observacao=body.observacao)
        local.add(recibo)
        local.flush()
        audit(local, usuario.id, 'recebimento_declarado_fornecedor', 'recebimentos_fornecedor', recibo.id,
            depois={'pagamento_id': p.id, 'valor_declarado': p.valor, 'referencia': body.referencia})
        local.commit()
        return recibo_out(recibo, p)


@router.patch('/{organizacao_id}/membros/{user_id}')
@transacao_segura
def alterar_membro(organizacao_id: int, user_id: int, body: MembroOrganizacaoIn,
                   db: Session = Depends(get_control_db), usuario: User = Depends(current_user)):
    bloquear_organizacao(db, organizacao_id)
    exigir_vinculo(db, usuario, organizacao_id, admin=True)
    membro = db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.organizacao_id == organizacao_id,
        VinculoOrganizacao.user_id == user_id).with_for_update())
    if not membro:
        raise HTTPException(404, 'Membro não encontrado')
    alvo = db.get(User, user_id)
    if not alvo:
        raise HTTPException(404, 'Membro não encontrado')
    if organizacao_id == 1 and body.perfil != 'fornecedor' and body.perfil != alvo.perfil:
        raise HTTPException(409, 'Na loja original, o perfil interno precisa corresponder ao perfil da conta')
    identidade = db.scalar(select(FornecedorIdentidade.id).where(FornecedorIdentidade.user_id == user_id))
    if (membro.perfil == 'fornecedor' or identidade) and body.perfil != membro.perfil:
        raise HTTPException(409, 'Identidade de fornecedor não pode receber outro perfil por esta operação')
    if body.perfil == 'fornecedor' and membro.perfil != 'fornecedor':
        raise HTTPException(409, 'Fornecedor precisa aceitar convite próprio')
    if membro.perfil == 'admin' and membro.ativo and (organizacao_id != 1 or alvo.perfil == 'admin') and (not body.ativo or body.perfil != 'admin'):
        consulta_admins = select(func.count()).select_from(VinculoOrganizacao).join(User).where(
            VinculoOrganizacao.organizacao_id == organizacao_id, VinculoOrganizacao.perfil == 'admin',
            VinculoOrganizacao.ativo.is_(True), User.ativo.is_(True))
        if organizacao_id == 1:
            consulta_admins = consulta_admins.where(User.perfil == 'admin')
        admins = db.scalar(consulta_admins)
        if admins <= 1:
            raise HTTPException(409, 'A loja precisa manter um administrador ativo')
    membro.perfil, membro.ativo = body.perfil, body.ativo
    audit(db, usuario.id, 'membro_organizacao_alterado', 'organizacao', organizacao_id,
        depois={'user_id': user_id, 'perfil': body.perfil, 'ativo': body.ativo})
    db.commit()
    return {'user_id': user_id, 'perfil': membro.perfil, 'ativo': membro.ativo}


@router.post('/{organizacao_id}/membros', status_code=201)
@transacao_segura
def adicionar_membro(organizacao_id: int, body: AdicionarMembroIn,
                     db: Session = Depends(get_control_db), usuario: User = Depends(current_user)):
    bloquear_organizacao(db, organizacao_id)
    exigir_vinculo(db, usuario, organizacao_id, admin=True)
    alvo = db.scalar(select(User).where(func.lower(func.trim(User.email)) == body.email.lower(), User.ativo.is_(True)))
    if not alvo or alvo.perfil == 'fornecedor' or db.scalar(select(FornecedorIdentidade.id).where(FornecedorIdentidade.user_id == alvo.id)):
        raise HTTPException(404, 'Conta interna disponível não encontrada')
    if organizacao_id == 1 and body.perfil != alvo.perfil:
        raise HTTPException(409, 'Na loja original, o perfil interno precisa corresponder ao perfil da conta')
    membro = db.scalar(select(VinculoOrganizacao).where(VinculoOrganizacao.organizacao_id == organizacao_id,
        VinculoOrganizacao.user_id == alvo.id))
    if membro:
        raise HTTPException(409, 'Conta já vinculada; use a edição do membro')
    db.add(VinculoOrganizacao(user_id=alvo.id, organizacao_id=organizacao_id, perfil=body.perfil, ativo=True))
    audit(db, usuario.id, 'membro_organizacao_adicionado', 'organizacao', organizacao_id,
        depois={'user_id': alvo.id, 'perfil': body.perfil})
    db.commit()
    return {'user_id': alvo.id, 'perfil': body.perfil, 'ativo': True}

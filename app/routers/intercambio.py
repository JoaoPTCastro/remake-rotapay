"""Intercâmbio CSV explícito de cadastros e obrigações novas, sem movimentos financeiros."""
import base64
import csv
import hashlib
import hmac
import io
import json
import re
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..auth import need
from ..audit import audit
from ..cadastros import hoje, backfill_pessoas
from ..config import SECRET_KEY
from ..database import get_db
from ..importacao_identidade import bloquear_cadastros, documento_normalizado
from ..models import Pessoa, NotaObrigacao, NotaAbatimento, ImportacaoCSV, ImportacaoCSVChave
from ..notas_schemas import NotaIn
from ..schemas import PessoaIn
from .notas import _consulta_notas, _out

r = APIRouter(prefix="/csv", tags=["intercambio"])
LEITURA = need("admin", "financeiro", "operador", "consulta")
ESCRITA = need("admin", "financeiro")
MAX_BYTES = 1024 * 1024
MAX_LINHAS = 500
MAX_EXPORT = 10000
HEADERS = {
    "cadastros": "tipo;nome;documento;telefone;email;apelido;endereco;observacoes;prazo_dias".split(";"),
    "notas": "documento_pessoa;relacao;numero_documento;valor_original;data_emissao;modo_vencimento;prazo_dias;vencimento;descricao".split(";"),
    "pagamentos": "tipo;forma;valor;data;documento_cliente;documento_fornecedor;referencia_externa;observacao".split(";")}


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _csv(headers, rows, filename):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", lineterminator="\r\n")
    monetarias = {"valor_original", "valor_abatido", "saldo_aberto", "valor"}
    def cell(value, coluna):
        if value is None:
            return ""
        if coluna in monetarias:
            return f"{Decimal(str(value)):.2f}".replace(".", ",")
        value = str(value)
        # Células que planilhas podem interpretar como fórmula, inclusive após espaços.
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")) or value.startswith(("\t", "\r", "\n")) else value
    writer.writerow(headers)
    for row in rows:
        writer.writerow([cell(row.get(k), k) for k in headers])
    return Response(b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8"), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})


def _data(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value, "%d/%m/%Y").date()


async def _arquivo(f):
    raw = await f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "CSV excede 1 MB")
    return raw


def _parse(raw, tipo):
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
        header = next(reader)
        if header != HEADERS[tipo]:
            raise HTTPException(422, "Cabeçalho inválido; baixe o modelo CSV")
        rows = []
        for values in reader:
            if not any(v.strip() for v in values):
                continue
            if len(rows) >= MAX_LINHAS:
                raise HTTPException(413, "CSV excede 500 linhas de dados")
            if len(values) != len(header):
                rows.append((reader.line_num, None))
            else:
                rows.append((reader.line_num, dict(zip(header, (v.strip() for v in values)))))
        if not rows:
            raise HTTPException(422, "CSV sem linhas de dados")
        return rows
    except (UnicodeError, csv.Error, StopIteration):
        raise HTTPException(422, "CSV inválido: use UTF-8, separador ponto e vírgula e campos corretamente escapados")



def _erros_validacao(exc):
    labels = {"tipo": "Tipo", "nome": "Nome", "documento": "Documento", "telefone": "Telefone", "email": "E-mail",
        "apelido": "Apelido", "endereco": "Endereço", "observacoes": "Observações", "prazo_dias": "Prazo em dias",
        "relacao": "Relação", "numero_documento": "Número do documento", "valor_original": "Valor original",
        "data_emissao": "Data de emissão", "modo_vencimento": "Modo de vencimento", "vencimento": "Vencimento", "descricao": "Descrição"}
    messages = {"string_too_short": "texto abaixo do tamanho mínimo", "string_too_long": "texto acima do tamanho máximo",
        "greater_than": "deve ser maior que o mínimo permitido", "greater_than_equal": "abaixo do mínimo permitido",
        "less_than_equal": "acima do máximo permitido", "literal_error": "opção inválida; use as opções do modelo",
        "string_pattern_mismatch": "formato inválido; use as opções do modelo", "decimal_max_digits": "valor acima do limite monetário",
        "decimal_max_places": "valor exige no máximo duas casas decimais", "date_type": "data obrigatória"}
    result = []
    for error in exc.errors(include_url=False, include_input=False):
        label = labels.get(str(error["loc"][-1]), "Linha") if error["loc"] else "Linha"
        message = error["msg"].removeprefix("Value error, ") if error["type"] == "value_error" else messages.get(error["type"], "valor inválido para este campo")
        result.append(f"{label}: {message}")
    return result


def _preview(db, tipo, raw):
    personmap = {}
    namemap = {}
    for p in db.query(Pessoa).all():
        personmap.setdefault(documento_normalizado(p.documento), []).append(p)
        namemap.setdefault(p.nome.strip().casefold(), []).append(p)
    existingnotes = {}
    histories = set()
    if tipo == "notas":
        existingnotes = {(n.pessoa_id, n.relacao, n.numero_documento): n for n in db.query(NotaObrigacao).all()}
        histories = {nid for nid, in db.query(NotaAbatimento.nota_id).distinct().all()}
    seen = set()
    seen_names = set()
    result = []
    for line, row in _parse(raw, tipo):
        item = {"linha": line, "status": "novo", "erros": [], "dados": {}}
        try:
            if row is None:
                raise ValueError("Quantidade de colunas diferente do cabeçalho")
            rawdoc = row["documento" if tipo == "cadastros" else "documento_pessoa"]
            if not re.fullmatch(r"[0-9. /-]+", rawdoc):
                raise ValueError("Documento deve conter somente dígitos e pontuação de CPF/CNPJ")
            doc = documento_normalizado(rawdoc)
            if len(doc) not in (11, 14):
                raise ValueError("Documento obrigatório no formato CPF (11 dígitos) ou CNPJ (14 dígitos)")
            matches = personmap.get(doc, [])
            if len(matches) > 1:
                raise ValueError("Documento ambíguo em cadastros existentes; revise manualmente")
            if tipo == "cadastros":
                values = dict(row, documento=doc, prazo_dias=int(row["prazo_dias"] or "0"))
                body = PessoaIn.model_validate(values)
                data = {k: getattr(body, k) for k in HEADERS[tipo]}
                data["tipo"] = "representante" if body.tipo == "cliente" else body.tipo
                identity = doc
                namekey = body.nome.strip().casefold()
                if namekey in seen_names:
                    raise ValueError("Nome repetido dentro do arquivo; revise a identidade manualmente")
                seen_names.add(namekey)
                if matches:
                    p = matches[0]
                    old = {k: getattr(p, k) for k in HEADERS[tipo]}
                    old["documento"] = documento_normalizado(p.documento)
                    if old != data or not p.ativo:
                        raise ValueError("Documento existente com dados diferentes; importação não sobrescreve cadastros")
                    item.update(status="ignorado", existente_id=p.id)
                elif namemap.get(body.nome.strip().casefold()):
                    raise ValueError("Nome já utilizado com outro documento; revise a identidade manualmente")
                item["dados"] = data
            else:
                if not matches:
                    raise ValueError("Documento não encontrado; importe o cadastro primeiro")
                p = matches[0]
                if not re.fullmatch(r"[0-9]+,[0-9]{2}", row["valor_original"]):
                    raise ValueError("Valor deve ter duas casas decimais com vírgula, sem separador de milhar")
                body = NotaIn(pessoa_id=p.id, relacao=row["relacao"], numero_documento=row["numero_documento"],
                    valor_original=Decimal(row["valor_original"].replace(",", ".")), data_emissao=_data(row["data_emissao"]),
                    modo_vencimento=row["modo_vencimento"] or "prazo_cadastro", prazo_dias=int(row["prazo_dias"]) if row["prazo_dias"] else None,
                    vencimento=_data(row["vencimento"]), descricao=row["descricao"])
                if not p.ativo or p.tipo not in ("ambos", "representante" if body.relacao == "cliente" else "fornecedor"):
                    raise ValueError("Cadastro deve estar ativo e possuir o papel da relação")
                prazo = p.prazo_dias if body.modo_vencimento == "prazo_cadastro" else body.prazo_dias
                venc = body.vencimento
                if body.modo_vencimento in ("prazo_cadastro", "prazo_informado"):
                    if prazo is None or not 0 <= prazo <= 36500:
                        raise ValueError("Prazo inválido")
                    venc = body.data_emissao + timedelta(days=prazo)
                data = dict(pessoa_id=p.id, relacao=body.relacao, numero_documento=body.numero_documento,
                    valor_original=f"{body.valor_original:.2f}", data_emissao=body.data_emissao.isoformat(),
                    vencimento=venc.isoformat() if venc else None, prazo_dias_snapshot=prazo,
                    modo_vencimento=body.modo_vencimento, descricao=body.descricao)
                identity = (p.id, body.relacao, body.numero_documento)
                n = existingnotes.get(identity)
                if n:
                    old = {k: getattr(n, k) for k in data}
                    old["valor_original"] = f"{Decimal(str(n.valor_original)):.2f}"
                    for k in ("data_emissao", "vencimento"):
                        old[k] = old[k].isoformat() if old[k] else None
                    if old != data or n.cancelada or n.id in histories:
                        raise ValueError("Nota existente divergente, cancelada ou com histórico; revisão manual necessária")
                    item.update(status="ignorado", existente_id=n.id)
                item["dados"] = data
                # Contexto de titular torna mudanças no cadastro detectáveis pela assinatura.
                item["contexto"] = {"pessoa_id": p.id, "tipo": p.tipo, "ativo": p.ativo, "prazo_dias": p.prazo_dias, "documento": doc}
            if identity in seen:
                raise ValueError("Identidade repetida dentro do arquivo")
            seen.add(identity)
        except (ValueError, ValidationError, OverflowError) as exc:
            item["status"] = "erro"
            item["erros"] = _erros_validacao(exc) if isinstance(exc, ValidationError) else [str(exc)]
        result.append(item)
    summary = {"total": len(result), "novos": sum(i["status"] == "novo" for i in result),
               "ignorados": sum(i["status"] == "ignorado" for i in result), "erros": sum(i["status"] == "erro" for i in result)}
    return {"tipo": tipo, "hash_conteudo": hashlib.sha256(raw).hexdigest(), "pode_importar": not summary["erros"], "resumo": summary, "linhas": result}


def _sign(uid, preview, exp):
    payload = {"user": uid, "exp": exp, "tipo": preview["tipo"], "hash_conteudo": preview["hash_conteudo"], "snapshot": hashlib.sha256(_json(preview).encode()).hexdigest()}
    encoded = base64.urlsafe_b64encode(_json(payload).encode()).decode()
    return encoded + "." + hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()


def _provar(token, uid, tipo, digest):
    try:
        encoded, signature = token.split(".")
        expected = hmac.new(SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        payload = json.loads(base64.urlsafe_b64decode(encoded))
        if not hmac.compare_digest(expected, signature) or payload["user"] != uid or payload["exp"] < time.time() or payload.get("tipo") != tipo or payload.get("hash_conteudo") != digest:
            raise ValueError()
        return payload
    except Exception:
        raise HTTPException(409, "Token de prévia inválido, expirado, de outro arquivo ou usuário")


def _validate(token, uid, preview):
    payload = _provar(token, uid, preview["tipo"], preview["hash_conteudo"])
    if token != _sign(uid, preview, payload["exp"]):
        raise HTTPException(409, "Prévia obsoleta ou arquivo alterado; gere uma nova prévia")


@r.get("/modelos/{tipo}")
def modelo(tipo: Literal["cadastros", "notas", "pagamentos"], u=Depends(LEITURA)):
    return _csv(HEADERS[tipo], [], f"modelo-{tipo}.csv")


@r.post("/{tipo}/previa")
async def previa(tipo: Literal["cadastros", "notas"], f: UploadFile = File(...), db: Session = Depends(get_db), u=Depends(ESCRITA)):
    preview = _preview(db, tipo, await _arquivo(f))
    preview["token_previa"] = _sign(u.id, preview, int(time.time()) + 900) if preview["pode_importar"] else ""
    return preview


@r.post("/{tipo}/importar")
async def importar(tipo: Literal["cadastros", "notas"], f: UploadFile = File(...), token_previa: str = Form(...),
    chave_idempotencia: str = Form(..., min_length=1, max_length=80), confirmacao: bool = Form(...),
    db: Session = Depends(get_db), u=Depends(ESCRITA)):
    if not confirmacao:
        raise HTTPException(422, "Confirmação explícita obrigatória")
    raw = await _arquivo(f)
    digest = hashlib.sha256(raw).hexdigest()
    bloquear_cadastros(db)
    alias = db.query(ImportacaoCSVChave).filter_by(created_by=u.id, chave_idempotencia=chave_idempotencia).first()
    prior = db.get(ImportacaoCSV, alias.importacao_id) if alias else db.query(ImportacaoCSV).filter_by(created_by=u.id, chave_idempotencia=chave_idempotencia).first()
    if prior:
        if prior.tipo != tipo or prior.hash_conteudo != digest:
            raise HTTPException(409, "Chave de idempotência utilizada com outro arquivo ou tipo")
        _provar(token_previa, u.id, tipo, digest)
        return {**json.loads(prior.resultado_json), "repetida": True}
    # Uma repetição reconhecida retorna o recibo anterior, nunca escreve o domínio novamente.
    _provar(token_previa, u.id, tipo, digest)
    prior = db.query(ImportacaoCSV).filter_by(tipo=tipo, hash_conteudo=digest).first()
    if prior:
        db.add(ImportacaoCSVChave(importacao_id=prior.id, created_by=u.id, chave_idempotencia=chave_idempotencia))
        audit(db, u.id, "csv_recibo_reutilizado", "importacoes_csv", prior.id, depois={"tipo": tipo, "hash_conteudo": digest})
        db.commit()
        return {**json.loads(prior.resultado_json), "repetida": True}
    preview = _preview(db, tipo, raw)
    if not preview["pode_importar"]:
        raise HTTPException(422, {"mensagem": "Lote inválido; nenhuma linha foi importada", "previa": preview})
    _validate(token_previa, u.id, preview)
    created, ignored = [], []
    try:
        for item in preview["linhas"]:
            if item["status"] == "ignorado":
                ignored.append(item["existente_id"])
                continue
            values = dict(item["dados"])
            if tipo == "cadastros":
                obj = Pessoa(**values)
            else:
                values["valor_original"] = float(values["valor_original"])
                for k in ("data_emissao", "vencimento"):
                    values[k] = date.fromisoformat(values[k]) if values[k] else None
                obj = NotaObrigacao(**values, created_by=u.id)
            db.add(obj)
            db.flush()
            created.append(obj.id)
            if tipo == "cadastros":
                backfill_pessoas(db, obj.id)
            audit(db, u.id, "csv_cadastro_criado" if tipo == "cadastros" else "csv_nota_criada", obj.__tablename__, obj.id,
                  depois={"hash_conteudo": digest, "linha": item["linha"]})
        ledger = ImportacaoCSV(tipo=tipo, hash_conteudo=digest, chave_idempotencia=chave_idempotencia, created_by=u.id, resultado_json="{}")
        db.add(ledger)
        db.flush()
        result = {"importacao_id": ledger.id, "tipo": tipo, "resumo": preview["resumo"], "ids_criados": created, "ids_ignorados": ignored, "repetida": False}
        ledger.resultado_json = _json(result)
        db.add(ImportacaoCSVChave(importacao_id=ledger.id, created_by=u.id, chave_idempotencia=chave_idempotencia))
        audit(db, u.id, "csv_importado", "importacoes_csv", ledger.id, depois={"tipo": tipo, "resumo": preview["resumo"], "hash_conteudo": digest})
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Cadastros ou notas alterados simultaneamente; gere nova prévia")


@r.get("/exportar/cadastros")
def export_cadastros(q: str = "", tipo: Literal["cliente", "representante", "fornecedor", "ambos"] | None = None,
    ativo: bool | None = None, db: Session = Depends(get_db), u=Depends(LEITURA)):
    query = db.query(Pessoa)
    if q:
        query = query.filter(Pessoa.nome.ilike(f"%{q}%"))
    if tipo:
        query = query.filter(Pessoa.tipo == ("representante" if tipo == "cliente" else tipo))
    if ativo is not None:
        query = query.filter(Pessoa.ativo == ativo)
    rows = query.order_by(Pessoa.id).limit(MAX_EXPORT + 1).all()
    if len(rows) > MAX_EXPORT:
        raise HTTPException(413, "Exportação excede 10000 registros; refine os filtros")
    return _csv(HEADERS["cadastros"], [{k: getattr(p, k) for k in HEADERS["cadastros"]} for p in rows], "cadastros" + (f"-{tipo}" if tipo else "") + ("-ativos" if ativo is True else "-inativos" if ativo is False else "") + ("-busca" if q else "") + ".csv")


@r.get("/exportar/notas")
def export_notas(pessoa_id: int | None = None, relacao: Literal["cliente", "fornecedor"] | None = None,
    status: Literal["aberto", "parcial", "quitado", "cancelado"] | None = None,
    data_de: date | None = None, data_ate: date | None = None, db: Session = Depends(get_db), u=Depends(LEITURA)):
    if data_de and data_ate and data_de > data_ate:
        raise HTTPException(422, "Período invertido")
    query, estado, _ = _consulta_notas(db)
    if pessoa_id:
        query = query.filter(NotaObrigacao.pessoa_id == pessoa_id)
    if relacao:
        query = query.filter(NotaObrigacao.relacao == relacao)
    if status:
        query = query.filter(estado == status)
    if data_de:
        query = query.filter(NotaObrigacao.data_emissao >= data_de)
    if data_ate:
        query = query.filter(NotaObrigacao.data_emissao <= data_ate)
    rows = query.order_by(NotaObrigacao.id).limit(MAX_EXPORT + 1).all()
    if len(rows) > MAX_EXPORT:
        raise HTTPException(413, "Exportação excede 10000 registros; refine os filtros")
    people = {p.id: p for p in db.query(Pessoa).filter(Pessoa.id.in_({n.pessoa_id for n, _, _ in rows})).all()}
    headers = ["id", "documento_pessoa", "pessoa_nome", "relacao", "numero_documento", "valor_original", "valor_abatido", "saldo_aberto", "status", "data_emissao", "vencimento", "modo_vencimento", "prazo_dias_snapshot", "descricao"]
    data = []
    for n, total, name in rows:
        values = _out(db, n, total, name)
        values["documento_pessoa"] = people[n.pessoa_id].documento
        data.append(values)
    return _csv(headers, data, "notas" + (f"-pessoa-{pessoa_id}" if pessoa_id else "") + (f"-{relacao}" if relacao else "") + (f"-{status}" if status else "") + (f"-de-{data_de}" if data_de else "") + (f"-ate-{data_ate}" if data_ate else "") + ".csv")

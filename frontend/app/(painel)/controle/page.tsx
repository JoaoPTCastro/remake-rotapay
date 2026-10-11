import Extrato from "../../../components/Extrato";

type SP = { [k: string]: string | string[] | undefined };

function str(v: string | string[] | undefined) {
  return typeof v === "string" ? v : "";
}

export default async function Controle({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  return (
    <div>
      <h1>Controle de saídas</h1>
      <p className="muted">Consulte, filtre e exporte os registros. Abra cada PIX ou siga para a conciliação sem alterar o fluxo de registro rápido.</p>
      <Extrato
        filtros={{
          q: str(sp.q), representante_id: str(sp.representante_id),
          fornecedor_id: str(sp.fornecedor_id), status: str(sp.status),
          data_ini: str(sp.data_ini), data_fim: str(sp.data_fim),
          chave: str(sp.chave), com_link: str(sp.com_link),
        }}
        modo="controle"
      />
    </div>
  );
}

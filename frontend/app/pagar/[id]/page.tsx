import { notFound } from "next/navigation";
import PagarForm from "../../../components/PagarForm";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export default async function Pagar({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const res = await fetch(`${API_URL}/chave-pix/${id}`, { cache: "no-store" });
  if (!res.ok) notFound();
  const dados = await res.json();
  return (
    <div>
      <PagarForm dados={dados} />
    </div>
  );
}

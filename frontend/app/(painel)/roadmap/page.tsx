import { CHANGELOG } from "../../../lib/changelog";
import { Clock } from "lucide-react";

const PENDENCIAS = [
  {
    t: "OCR real do comprovante",
    d: "Ler de verdade o comprovante (valor, data, remetente, chave) e auxiliar a revisão dos comprovantes anexados às movimentações. Hoje a leitura é experimental/simulada.",
    nota: "A fazer: decidir o provedor — Gemini ou Google Vision (nuvem, melhor leitura, envia comprovantes a terceiros) ou Tesseract local (privado, leitura mais fraca). Depois plugar no mesmo contrato de app/ocr.py (função extrair) e trocar os rótulos de 'simulado' nas telas.",
  },
  {
    t: "Backfill de link_token nos PIX antigos",
    d: "PIX registrados antes dos links não aparecem no quadro 'PIX rastreáveis' do Início.",
    nota: "A fazer: junto com o OCR (ou antes), definir a regra de associação de comprovantes antigos aos links, com revisão manual para não ligar errado.",
  },
  {
    t: "Hardening para Postgres",
    d: "Proteções que o SQLite esconde hoje: corrida no 'último admin ativo' e jobs duplicados.",
    nota: "A fazer: na migração para Postgres, adicionar constraint única em jobs(tipo, ref_id) e lock/transação na troca de perfil dos admins.",
  },
  {
    t: "Validar regra do rodízio com o João",
    d: "A fila ordena por prioridade, nota mais antiga e menor faltante — reconstrução da lógica da planilha a partir da reunião.",
    nota: "A fazer: ouvir os áudios do João página a página e ajustar a ordem se a planilha priorizar diferente (ex.: menor faltante antes da data). Previsto como ajuste, sem replanejar.",
  },

  {
    t: "Deploy estável (VPS ou pago)",
    d: "A demo zera o banco a cada deploy; o João precisa de base estável para testar e gravar feedbacks.",
    nota: "A fazer quando decidir: subir compose com disco (ou Render pago), seed-prod com SETUP_TOKEN e entregar o acesso. Nada de código muda.",
  },
  {
    t: "Fonte oficial da chave PIX (PSP ou local)",
    d: "Hoje: chave cadastrada + BR-Code local + Checkto. Falta decidir se haverá PSP/banco para QR dinâmico.",
    nota: "A fazer: resposta da pergunta aberta da reunião; se PSP, vira conector separado sem mexer no fluxo atual.",
  },
];

export default function Roadmap() {
  return (
    <div>
      <h1>Roadmap — o que mudou e o que vem</h1>
      <p className="muted">Histórico de entregas do painel, do início até agora. Versão beta (MVP).</p>

      <section className="painel" aria-label="Pendências">
        <h2><Clock size={18} /> A fazer — pendências anotadas</h2>
        <p className="muted">Nada disso é bloqueante hoje; são os próximos passos combinados.</p>
        <div className="steps">
          {PENDENCIAS.map((p) => (
            <div className="step" key={p.t}>
              <span className="n">→</span>
              <div>
                <strong>{p.t}</strong>
                <p className="muted">{p.d}</p>
                <p className="muted" style={{ fontSize: 13 }}>{p.nota}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <h2 style={{ marginTop: 24 }}>Entregue</h2>
      <div className="steps">
        {CHANGELOG.map((m) => (
          <div className="step" key={m.data + m.titulo}>
            <span className="n">✓</span>
            <div>
              <strong>{m.titulo}</strong> <span className="muted">· {m.data}</span>
              <ul className="muted">
                {m.itens.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
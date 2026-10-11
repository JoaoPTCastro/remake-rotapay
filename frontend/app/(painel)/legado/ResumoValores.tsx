export default function ResumoValores({ valores }: { valores: Record<string, number | null> }) {
  const dinheiro = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  return <div className="tablewrap"><table><thead><tr><th>Valor registrado</th><th>Montante</th></tr></thead><tbody>{Object.entries(valores).map(([campo,valor]) => <tr key={campo}><td data-label="Valor registrado">{campo.replaceAll("_", " ")}</td><td data-label="Montante">{valor === null ? "Não informado" : dinheiro.format(valor)}</td></tr>)}</tbody></table></div>;
}

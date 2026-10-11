"use client";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import PdfComprovante from "./PdfComprovante";
import styles from "./ComprovanteViewer.module.css";
type ArquivoVisual = { url: string; mime: string; blob: Blob };
export default function ComprovanteViewer({ pagamentoId, anexoId, nome }: { pagamentoId: number; anexoId: number; nome: string }) {
  const dialogo = useRef<HTMLDialogElement>(null); const gatilho = useRef<HTMLButtonElement>(null);
  const controller = useRef<AbortController | null>(null); const blobUrl = useRef<string | null>(null);
  const [expandido, setExpandido] = useState(false);
  const [arquivo, setArquivo] = useState<ArquivoVisual | null>(null); const [erro, setErro] = useState(""); const [carregando, setCarregando] = useState(false); const [zoom, setZoom] = useState(100);
  const download = `/api/pagamentos/anexo?pagamento=${pagamentoId}&anexo=${anexoId}`;
  useEffect(() => () => { controller.current?.abort(); if (blobUrl.current) URL.revokeObjectURL(blobUrl.current); }, []);
  function fechar() { setExpandido(false); if (document.fullscreenElement === dialogo.current) void document.exitFullscreen().catch(() => undefined); controller.current?.abort(); controller.current = null; if (blobUrl.current) URL.revokeObjectURL(blobUrl.current); blobUrl.current = null; setArquivo(null); setCarregando(false); dialogo.current?.close(); gatilho.current?.focus(); }
  async function abrir() {
    if (dialogo.current?.open) return; dialogo.current?.showModal(); setErro(""); setZoom(100); setExpandido(false); setCarregando(true);
    const c = new AbortController(); controller.current = c;
    try { const { blob, mime } = await baixarVisualizacao(`${download}&modo=inline`, c.signal); if (c.signal.aborted) return; const url = URL.createObjectURL(blob); blobUrl.current = url; setArquivo({ url, mime, blob }); }
    catch (e) { if (!c.signal.aborted) setErro(e instanceof Error ? e.message : "Não foi possível abrir o comprovante."); }
    finally { if (controller.current === c) setCarregando(false); }
  }
  async function telaCheia() { if (expandido) { setExpandido(false); if (document.fullscreenElement) await document.exitFullscreen().catch(() => undefined); return; } setExpandido(true); try { await dialogo.current?.requestFullscreen(); } catch { /* A classe ampliada ocupa a janela mesmo sem permissão para fullscreen nativo. */ } }

  return <><button ref={gatilho} type="button" onClick={() => { void abrir(); }}>Visualizar comprovante</button><dialog ref={dialogo} className={`${styles.dialogo} ${expandido ? styles.expandido : ""}`} aria-label={`Comprovante: ${nome}`} onCancel={e => { e.preventDefault(); fechar(); }}><div className={styles.conteudo}><header className={styles.barra}><h2>{nome}</h2><button type="button" onClick={() => { void telaCheia(); }}>{expandido ? "Voltar à janela" : "Tela cheia"}</button><a href={download}>Baixar original</a><button type="button" onClick={fechar} autoFocus>Fechar</button></header><p className={styles.aviso}>Arquivo privado anexado ao pagamento. A imagem ou PDF não confirma conciliação nem valida o conteúdo automaticamente.</p>{carregando && <p role="status">Carregando comprovante…</p>}{erro && <p role="alert" className={styles.erro}>{erro}</p>}{arquivo && (arquivo.mime === "application/pdf" ? <PdfComprovante blob={arquivo.blob} nome={nome} /> : <><Zoom mime={arquivo.mime} zoom={zoom} alterar={setZoom} /><div className={styles.area}><Image src={arquivo.url} alt={`Comprovante anexado: ${nome}`} width={1600} height={1200} unoptimized style={{ width: `${zoom}%`, height: "auto", maxWidth: "none" }} /></div></>)}<p className={styles.aviso}>Tela cheia ocupa a janela quando o navegador não permite o modo nativo. Escape fecha a visualização.</p></div></dialog></>;
}
function Zoom({ mime, zoom, alterar }: { mime: string; zoom: number; alterar: (v: number) => void }) { if (mime === "application/pdf") return null; return <div className={styles.barra}><button type="button" disabled={zoom <= 50} onClick={() => alterar(Math.max(50, zoom - 25))} aria-label="Diminuir imagem">−</button><span>{zoom}%</span><button type="button" disabled={zoom >= 300} onClick={() => alterar(Math.min(300, zoom + 25))} aria-label="Ampliar imagem">+</button><button type="button" onClick={() => alterar(100)}>Restaurar zoom</button></div>; }

async function baixarVisualizacao(url: string, signal: AbortSignal) { const resposta = await fetch(url, { signal, cache: "no-store" }); if (!resposta.ok) throw new Error("Comprovante indisponível para visualização. Você pode tentar baixar o arquivo."); const mime = resposta.headers.get("content-type")?.split(";")[0] ?? ""; if (!["image/jpeg", "image/png", "image/webp", "application/pdf"].includes(mime)) throw new Error("Este formato permite apenas download."); return { blob: await resposta.blob(), mime }; }

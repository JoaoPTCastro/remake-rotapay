"use client";
import { useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";
import styles from "./ComprovanteViewer.module.css";
export default function PdfComprovante({ blob, nome }: { blob: Blob; nome: string }) {
  const [documento, setDocumento] = useState<PDFDocumentProxy | null>(null);
  const [erro, setErro] = useState(""); const [pagina, setPagina] = useState(1); const [zoom, setZoom] = useState(100);
  useEffect(() => {
    let descartado = false; let carregamento: ReturnType<typeof import("pdfjs-dist")["getDocument"]> | null = null;
    void (async () => { try { const pdfjs = await import("pdfjs-dist"); if (descartado) return; pdfjs.GlobalWorkerOptions.workerSrc = "/pdfjs/6.3.289/pdf.worker.min.mjs"; const dados = new Uint8Array(await blob.arrayBuffer()); if (descartado) return; const opcoes = { data: dados, isEvalSupported: false, enableXfa: false, useWorkerFetch: false, useWasm: false, useSystemFonts: true, disableAutoFetch: true, disableStream: true, maxImageSize: 16_777_216, canvasMaxAreaInBytes: 32_000_000 }; carregamento = pdfjs.getDocument(opcoes); const pdf = await carregamento.promise; if (pdf.numPages > 500) throw new Error("O PDF excede 500 páginas. Baixe o original para conferência."); if (!descartado) setDocumento(pdf); } catch (e) { if (!descartado) setErro(e instanceof Error && e.message.startsWith("O PDF excede") ? e.message : "Não foi possível renderizar este PDF. Baixe o original para conferência."); } })();
    return () => { descartado = true; if (carregamento) void carregamento.destroy().catch(() => undefined); };
  }, [blob]);
  return <>{erro && <p role="alert" className={styles.erro}>{erro}</p>}{!documento && !erro && <p role="status">Preparando PDF privado…</p>}{documento && <><div className={styles.barra}><button type="button" disabled={pagina === 1} onClick={() => setPagina(p => p - 1)}>Página anterior</button><span>Página {pagina} de {documento.numPages}</span><button type="button" disabled={pagina === documento.numPages} onClick={() => setPagina(p => p + 1)}>Próxima página</button><button type="button" disabled={zoom <= 50} onClick={() => setZoom(z => z - 25)} aria-label="Diminuir PDF">−</button><span>{zoom}%</span><button type="button" disabled={zoom >= 300} onClick={() => setZoom(z => z + 25)} aria-label="Ampliar PDF">+</button><button type="button" onClick={() => setZoom(100)}>Restaurar zoom</button></div><CanvasPdf key={`${pagina}-${zoom}`} documento={documento} pagina={pagina} zoom={zoom} nome={nome} /></>}<p className={styles.aviso}>Visualização somente em imagem da página, sem executar ações, scripts, links ou formulários do PDF. O original permanece disponível para baixar.</p></>;
}
function CanvasPdf({ documento, pagina, zoom, nome }: { documento: PDFDocumentProxy; pagina: number; zoom: number; nome: string }) {
  const canvas = useRef<HTMLCanvasElement>(null); const [erro, setErro] = useState(""); const [ocupado, setOcupado] = useState(true);
  useEffect(() => {
    let descartado = false; let render: ReturnType<Awaited<ReturnType<PDFDocumentProxy["getPage"]>>["render"]> | null = null;
    void (async () => { try { const folha = await documento.getPage(pagina); const elemento = canvas.current; if (descartado || !elemento) return; const viewport = viewportLimitado(folha, elemento, zoom); elemento.width = Math.floor(viewport.width); elemento.height = Math.floor(viewport.height); const context = elemento.getContext("2d"); if (!context) throw new Error("Canvas indisponível"); render = folha.render({ canvas: elemento, canvasContext: context, viewport }); await render.promise; if (!descartado) setOcupado(false); } catch { if (!descartado) { setErro("Não foi possível desenhar esta página. Baixe o original."); setOcupado(false); } } })();
    return () => { descartado = true; render?.cancel(); };
  }, [documento, pagina, zoom]);
  return <div className={styles.area}>{ocupado && <p role="status">Desenhando página…</p>}{erro && <p role="alert" className={styles.erro}>{erro}</p>}<canvas ref={canvas} className={styles.canvasPdf} role="img" aria-label={`Página ${pagina} do comprovante ${nome}`} /></div>;
}

function viewportLimitado(folha: PDFPageProxy, elemento: HTMLCanvasElement, zoom: number) { const area = folha.getViewport({ scale: 1 }); const largura = Math.max(200, (elemento.parentElement?.clientWidth ?? 800) - 24); const desejada = Math.min(1.5, largura / area.width) * zoom / 100; const escala = Math.min(desejada, 4096 / area.width, 4096 / area.height, Math.sqrt(8_000_000 / (area.width * area.height))); if (!Number.isFinite(escala) || escala <= 0) throw new Error("Página inválida"); return folha.getViewport({ scale: escala }); }

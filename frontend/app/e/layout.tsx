import type { Metadata } from "next";
export const metadata: Metadata = { title:"Extrato compartilhado — RotaPay", robots:{index:false,follow:false},referrer:"no-referrer" };
export default function LayoutExtratoCompartilhado({children}:{children:React.ReactNode}) {return <><header className="topbar"><strong>RotaPay · Extrato compartilhado</strong></header><main className="wrap">{children}</main></>;}

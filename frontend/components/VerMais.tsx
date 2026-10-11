"use client";

import { useState } from "react";

export default function VerMais({ total, limite, colSpan, children, extra }: {
  total: number; limite: number; colSpan: number;
  children: React.ReactNode; extra: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  if (total <= limite) return <>{children}</>;
  return (
    <>
      {children}
      {open && extra}
      <tr className="vermais">
        <td colSpan={colSpan} data-label="">
          <button type="button" className="secondary" onClick={() => setOpen(!open)}>
            {open ? "Ver menos" : `Ver mais (${total - limite})`}
          </button>
        </td>
      </tr>
    </>
  );
}

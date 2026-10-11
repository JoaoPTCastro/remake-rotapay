"use client";

import { useRouter } from "next/navigation";

export default function DismissTour() {
  const router = useRouter();
  return (
    <button
      type="button"
      className="secondary"
      onClick={async () => {
        await fetch("/api/tour", { method: "POST" });
        router.refresh();
      }}
    >
      Ocultar guia
    </button>
  );
}

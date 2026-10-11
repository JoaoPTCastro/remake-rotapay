"use client";

import { useRouter } from "next/navigation";

export default function LogoutButton() {
  const router = useRouter();
  return (
    <button
      type="button"
      className="link"
      onClick={async () => {
        await fetch("/api/logout", { method: "POST" });
        router.push("/login");
      }}
    >
      Sair
    </button>
  );
}

"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

export default function ThemeToggle() {
  const dark = useSyncExternalStore(
    (onChange) => {
      window.addEventListener("storage", onChange);
      return () => window.removeEventListener("storage", onChange);
    },
    () => localStorage.getItem("theme") === "dark",
    () => false,
  );

  function toggle() {
    const next = !dark;
    document.documentElement.dataset.theme = next ? "dark" : "light";
    localStorage.setItem("theme", next ? "dark" : "light");
    window.dispatchEvent(new StorageEvent("storage", { key: "theme", newValue: next ? "dark" : "light" }));
  }

  return (
    <button className="iconbtn" type="button" onClick={toggle} aria-label={dark ? "Usar tema claro" : "Usar tema escuro"}>
      {dark ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  );
}

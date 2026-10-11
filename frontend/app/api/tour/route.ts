import { NextResponse } from "next/server";

export async function POST() {
  const out = NextResponse.json({ ok: true });
  out.cookies.set("tour_off", "1", { path: "/", maxAge: 365 * 24 * 3600, sameSite: "lax" });
  return out;
}

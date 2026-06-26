"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Navbar() {
  const { user, logout, isSuperAdmin } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  const links = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/simulate", label: "Nuova simulazione" },
    { href: "/profile", label: "Profilo" },
  ];
  if (isSuperAdmin) links.push({ href: "/admin", label: "Admin" });

  return (
    <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="text-lg font-bold">
            <span className="text-green-400">Portfolio</span>Time
          </Link>
          <div className="hidden gap-1 sm:flex">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded px-3 py-1.5 text-sm transition ${
                  pathname === l.href
                    ? "bg-slate-800 text-white"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block">
            <div className="text-sm text-slate-200">{user?.full_name || user?.email}</div>
            <div className="text-xs text-slate-500">
              {isSuperAdmin ? "Super Admin" : "Utente"}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="rounded border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:border-red-500 hover:text-red-400"
          >
            Esci
          </button>
        </div>
      </div>

      {/* Link mobile */}
      <div className="flex gap-1 overflow-x-auto px-4 pb-2 sm:hidden">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`whitespace-nowrap rounded px-3 py-1.5 text-sm ${
              pathname === l.href ? "bg-slate-800 text-white" : "text-slate-400"
            }`}
          >
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

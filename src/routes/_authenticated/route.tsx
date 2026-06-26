import { createFileRoute, Outlet, redirect, Link, useNavigate } from "@tanstack/react-router";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { LayoutDashboard, ListOrdered, Activity, Settings, KeyRound, History, LogOut } from "lucide-react";

export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  beforeLoad: async () => {
    const { data } = await supabase.auth.getSession();
    if (!data.session) throw redirect({ to: "/auth" });
  },
  component: Shell,
});

function Shell() {
  const nav = useNavigate();
  async function signOut() {
    await supabase.auth.signOut();
    nav({ to: "/auth" });
  }
  const items = [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/positions", label: "Positions", icon: ListOrdered },
    { to: "/trades", label: "Trades", icon: History },
    { to: "/signals", label: "Signals", icon: Activity },
    { to: "/settings", label: "Settings", icon: Settings },
    { to: "/credentials", label: "Credentials", icon: KeyRound },
  ] as const;
  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background">
      <aside className="md:w-60 border-r bg-card flex md:flex-col">
        <div className="p-4 font-bold text-lg border-b md:block hidden">Delta Algo</div>
        <nav className="flex md:flex-col gap-1 p-2 flex-1 overflow-x-auto">
          {items.map((i) => (
            <Link
              key={i.to}
              to={i.to}
              className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent whitespace-nowrap"
              activeProps={{ className: "bg-accent text-accent-foreground" }}
            >
              <i.icon className="h-4 w-4" />
              <span>{i.label}</span>
            </Link>
          ))}
        </nav>
        <div className="p-2 border-t hidden md:block">
          <Button variant="ghost" className="w-full justify-start" onClick={signOut}>
            <LogOut className="h-4 w-4 mr-2" /> Sign out
          </Button>
        </div>
      </aside>
      <main className="flex-1 p-4 md:p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}

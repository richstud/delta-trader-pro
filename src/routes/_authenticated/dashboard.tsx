import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Summary = {
  mode: "paper" | "live";
  balance: number;
  equity: number;
  open_positions: number;
  pnl_today: number;
  pnl_total: number;
};
type Status = {
  websocket: boolean;
  redis: boolean;
  supabase: boolean;
  algo: boolean;
};

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — Delta Algo" }] }),
  component: Dashboard,
});

function Dashboard() {
  const summary = useQuery({
    queryKey: ["summary"],
    queryFn: () => api<Summary>("/account/summary"),
    refetchInterval: 5000,
  });
  const status = useQuery({
    queryKey: ["status"],
    queryFn: () => api<Status>("/status"),
    refetchInterval: 5000,
  });

  const s = summary.data;
  const st = status.data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat title="Mode" value={s?.mode?.toUpperCase() ?? "—"} />
        <Stat title="Balance" value={s ? `$${s.balance.toFixed(2)}` : "—"} />
        <Stat title="Equity" value={s ? `$${s.equity.toFixed(2)}` : "—"} />
        <Stat title="Open positions" value={s?.open_positions ?? "—"} />
        <Stat title="P&L today" value={s ? `$${s.pnl_today.toFixed(2)}` : "—"} accent={s && s.pnl_today >= 0 ? "pos" : "neg"} />
        <Stat title="P&L total" value={s ? `$${s.pnl_total.toFixed(2)}` : "—"} accent={s && s.pnl_total >= 0 ? "pos" : "neg"} />
      </div>

      <Card>
        <CardHeader><CardTitle>System status</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <StatusPill label="WebSocket" ok={st?.websocket} />
          <StatusPill label="Redis" ok={st?.redis} />
          <StatusPill label="Supabase" ok={st?.supabase} />
          <StatusPill label="Algo" ok={st?.algo} />
        </CardContent>
      </Card>

      {(summary.error || status.error) && (
        <div className="text-sm text-destructive">
          Backend unreachable. Check VITE_BACKEND_URL and that the FastAPI service is running.
        </div>
      )}
    </div>
  );
}

function Stat({ title, value, accent }: { title: string; value: React.ReactNode; accent?: "pos" | "neg" }) {
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground font-medium">{title}</CardTitle></CardHeader>
      <CardContent className={accent === "pos" ? "text-green-600 text-2xl font-bold" : accent === "neg" ? "text-red-600 text-2xl font-bold" : "text-2xl font-bold"}>
        {value}
      </CardContent>
    </Card>
  );
}
function StatusPill({ label, ok }: { label: string; ok?: boolean }) {
  return (
    <Badge variant={ok ? "default" : "destructive"}>
      <span className={`mr-2 inline-block h-2 w-2 rounded-full ${ok ? "bg-green-400" : "bg-red-300"}`} />
      {label}: {ok === undefined ? "…" : ok ? "OK" : "DOWN"}
    </Badge>
  );
}

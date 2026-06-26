import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Trade = {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  qty: number;
  price: number;
  pnl: number;
  mode: "paper" | "live";
  source: "algo" | "manual";
  executed_at: string;
};

export const Route = createFileRoute("/_authenticated/trades")({
  head: () => ({ meta: [{ title: "Trades — Delta Algo" }] }),
  component: TradesPage,
});

function TradesPage() {
  const q = useQuery({ queryKey: ["trades"], queryFn: () => api<Trade[]>("/trades"), refetchInterval: 6000 });
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Trade history</h1>
      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Side</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>PnL</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Source</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(q.data ?? []).map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{new Date(t.executed_at).toLocaleString()}</TableCell>
                  <TableCell>{t.symbol}</TableCell>
                  <TableCell className={t.side === "buy" ? "text-green-600" : "text-red-600"}>{t.side.toUpperCase()}</TableCell>
                  <TableCell>{t.qty}</TableCell>
                  <TableCell>{t.price}</TableCell>
                  <TableCell className={t.pnl >= 0 ? "text-green-600" : "text-red-600"}>{t.pnl.toFixed(2)}</TableCell>
                  <TableCell>{t.mode}</TableCell>
                  <TableCell>{t.source}</TableCell>
                </TableRow>
              ))}
              {q.data?.length === 0 && (
                <TableRow><TableCell colSpan={8} className="text-center text-muted-foreground">No trades yet</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

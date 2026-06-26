import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Signal = {
  id: string;
  ts: string;
  symbol: string;
  side: "buy" | "sell";
  ema6: number;
  ema50: number;
  price: number;
};

export const Route = createFileRoute("/_authenticated/signals")({
  head: () => ({ meta: [{ title: "Signals — Delta Algo" }] }),
  component: SignalsPage,
});

function SignalsPage() {
  const q = useQuery({ queryKey: ["signals"], queryFn: () => api<Signal[]>("/signals"), refetchInterval: 4000 });
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">EMA 6/50 signals</h1>
      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead><TableHead>Symbol</TableHead><TableHead>Side</TableHead>
                <TableHead>Price</TableHead><TableHead>EMA6</TableHead><TableHead>EMA50</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(q.data ?? []).map((s) => (
                <TableRow key={s.id}>
                  <TableCell>{new Date(s.ts).toLocaleString()}</TableCell>
                  <TableCell>{s.symbol}</TableCell>
                  <TableCell className={s.side === "buy" ? "text-green-600" : "text-red-600"}>{s.side.toUpperCase()}</TableCell>
                  <TableCell>{s.price}</TableCell>
                  <TableCell>{s.ema6.toFixed(2)}</TableCell>
                  <TableCell>{s.ema50.toFixed(2)}</TableCell>
                </TableRow>
              ))}
              {q.data?.length === 0 && (
                <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground">No signals yet</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

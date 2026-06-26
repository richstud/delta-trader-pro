import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useState } from "react";
import { toast } from "sonner";

type Position = {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  qty: number;
  entry_price: number;
  sl: number | null;
  tp: number | null;
  status: string;
  opened_at: string;
};

export const Route = createFileRoute("/_authenticated/positions")({
  head: () => ({ meta: [{ title: "Positions — Delta Algo" }] }),
  component: PositionsPage,
});

function PositionsPage() {
  const qc = useQueryClient();
  const positions = useQuery({
    queryKey: ["positions"],
    queryFn: () => api<Position[]>("/positions"),
    refetchInterval: 4000,
  });

  const close = useMutation({
    mutationFn: (id: string) => api(`/positions/${id}/close`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Close requested");
      qc.invalidateQueries({ queryKey: ["positions"] });
    },
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Positions</h1>

      <ManualOrder onPlaced={() => qc.invalidateQueries({ queryKey: ["positions"] })} />

      <Card>
        <CardHeader><CardTitle>Open positions</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Side</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Entry</TableHead>
                <TableHead>SL</TableHead>
                <TableHead>TP</TableHead>
                <TableHead>Opened</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(positions.data ?? []).map((p) => (
                <TableRow key={p.id}>
                  <TableCell>{p.symbol}</TableCell>
                  <TableCell className={p.side === "buy" ? "text-green-600" : "text-red-600"}>{p.side.toUpperCase()}</TableCell>
                  <TableCell>{p.qty}</TableCell>
                  <TableCell>{p.entry_price}</TableCell>
                  <TableCell>{p.sl ?? "—"}</TableCell>
                  <TableCell>{p.tp ?? "—"}</TableCell>
                  <TableCell>{new Date(p.opened_at).toLocaleString()}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="destructive" onClick={() => close.mutate(p.id)}>Close</Button>
                  </TableCell>
                </TableRow>
              ))}
              {positions.data?.length === 0 && (
                <TableRow><TableCell colSpan={8} className="text-center text-muted-foreground">No open positions</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function ManualOrder({ onPlaced }: { onPlaced: () => void }) {
  const [symbol, setSymbol] = useState("BTCUSD");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState("1");
  const place = useMutation({
    mutationFn: () => api("/manual/order", { method: "POST", body: JSON.stringify({ symbol, side, qty: Number(qty) }) }),
    onSuccess: () => { toast.success("Order placed"); onPlaced(); },
    onError: (e) => toast.error((e as Error).message),
  });
  return (
    <Card>
      <CardHeader><CardTitle>Manual order</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
        <div className="space-y-2"><Label>Symbol</Label><Input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} /></div>
        <div className="space-y-2"><Label>Side</Label>
          <Select value={side} onValueChange={(v) => setSide(v as "buy" | "sell")}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="buy">Buy</SelectItem><SelectItem value="sell">Sell</SelectItem></SelectContent>
          </Select>
        </div>
        <div className="space-y-2"><Label>Qty</Label><Input type="number" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
        <Button onClick={() => place.mutate()} disabled={place.isPending}>Place order</Button>
      </CardContent>
    </Card>
  );
}

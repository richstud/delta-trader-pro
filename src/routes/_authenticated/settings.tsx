import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useEffect, useState } from "react";
import { toast } from "sonner";

type Settings = {
  mode: "paper" | "live";
  default_qty: number;
  sl_pct: number;
  tp_pct: number;
  trailing_pct: number;
  symbols: string[];
};

export const Route = createFileRoute("/_authenticated/settings")({
  head: () => ({ meta: [{ title: "Settings — Delta Algo" }] }),
  component: SettingsPage,
});

function SettingsPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["settings"], queryFn: () => api<Settings>("/settings") });
  const [form, setForm] = useState<Settings>({
    mode: "paper", default_qty: 1, sl_pct: 1, tp_pct: 2, trailing_pct: 0, symbols: ["BTCUSD"],
  });
  useEffect(() => { if (q.data) setForm(q.data); }, [q.data]);

  const save = useMutation({
    mutationFn: () => api("/settings", { method: "PUT", body: JSON.stringify(form) }),
    onSuccess: () => { toast.success("Saved"); qc.invalidateQueries({ queryKey: ["settings"] }); },
    onError: (e) => toast.error((e as Error).message),
  });

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>
      <Card>
        <CardHeader><CardTitle>Trading parameters</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Mode</Label>
            <Select value={form.mode} onValueChange={(v) => setForm({ ...form, mode: v as "paper" | "live" })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="paper">Paper</SelectItem>
                <SelectItem value="live">Live</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Num label="Default qty" v={form.default_qty} on={(n) => setForm({ ...form, default_qty: n })} />
          <Num label="Stop loss %" v={form.sl_pct} on={(n) => setForm({ ...form, sl_pct: n })} />
          <Num label="Take profit %" v={form.tp_pct} on={(n) => setForm({ ...form, tp_pct: n })} />
          <Num label="Trailing stop % (0 to disable)" v={form.trailing_pct} on={(n) => setForm({ ...form, trailing_pct: n })} />
          <div className="space-y-2">
            <Label>Symbols (comma-separated)</Label>
            <Input value={form.symbols.join(",")} onChange={(e) => setForm({ ...form, symbols: e.target.value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean) })} />
          </div>
          <Button onClick={() => save.mutate()} disabled={save.isPending}>Save</Button>
        </CardContent>
      </Card>
    </div>
  );
}

function Num({ label, v, on }: { label: string; v: number; on: (n: number) => void }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input type="number" step="0.01" value={v} onChange={(e) => on(Number(e.target.value))} />
    </div>
  );
}

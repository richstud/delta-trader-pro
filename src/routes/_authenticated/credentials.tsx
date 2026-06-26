import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import { toast } from "sonner";

type Cred = { broker: string; has_credentials: boolean; is_active: boolean; updated_at: string | null };

export const Route = createFileRoute("/_authenticated/credentials")({
  head: () => ({ meta: [{ title: "Broker credentials — Delta Algo" }] }),
  component: CredsPage,
});

function CredsPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["creds"], queryFn: () => api<Cred>("/credentials") });
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");

  const save = useMutation({
    mutationFn: () => api("/credentials", { method: "PUT", body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret }) }),
    onSuccess: () => { toast.success("Saved (encrypted at rest)"); setApiKey(""); setApiSecret(""); qc.invalidateQueries({ queryKey: ["creds"] }); },
    onError: (e) => toast.error((e as Error).message),
  });
  const del = useMutation({
    mutationFn: () => api("/credentials", { method: "DELETE" }),
    onSuccess: () => { toast.success("Deleted"); qc.invalidateQueries({ queryKey: ["creds"] }); },
  });

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Delta Exchange credentials</h1>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Status
            {q.data?.has_credentials ? <Badge>Stored</Badge> : <Badge variant="secondary">Not set</Badge>}
            {q.data?.has_credentials && (q.data.is_active ? <Badge variant="default">Active</Badge> : <Badge variant="destructive">Inactive</Badge>)}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            API key and secret are encrypted server-side with AES-GCM and never displayed back. Submit blanks to no-op; use Delete to remove.
          </p>
          <div className="space-y-2"><Label>API Key</Label><Input value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="Paste Delta API key" /></div>
          <div className="space-y-2"><Label>API Secret</Label><Input type="password" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} placeholder="Paste Delta API secret" /></div>
          <div className="flex gap-2">
            <Button onClick={() => save.mutate()} disabled={!apiKey || !apiSecret || save.isPending}>Save</Button>
            {q.data?.has_credentials && <Button variant="destructive" onClick={() => del.mutate()}>Delete</Button>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

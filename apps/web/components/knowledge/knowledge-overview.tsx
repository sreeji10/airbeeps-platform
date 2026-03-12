import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const sources = [
  { title: "Support Docs", status: "Ready", chunks: 243 },
  { title: "Product Spec", status: "Processing", chunks: 87 },
  { title: "Security Playbook", status: "Ready", chunks: 64 },
];

export function KnowledgeOverview() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {sources.map((source) => (
        <Card key={source.title}>
          <CardHeader>
            <CardTitle className="text-base">{source.title}</CardTitle>
            <CardDescription>Status: {source.status}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Indexed chunks: {source.chunks}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

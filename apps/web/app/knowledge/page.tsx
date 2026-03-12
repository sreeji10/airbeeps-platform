import { KnowledgeOverview } from "@/components/knowledge/knowledge-overview";

export default function KnowledgePage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Knowledge</h1>
        <p className="text-sm text-muted-foreground">Source and ingestion status for workspace knowledge base.</p>
      </section>
      <KnowledgeOverview />
    </div>
  );
}

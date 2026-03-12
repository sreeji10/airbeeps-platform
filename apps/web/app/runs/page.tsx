import { RunsTable } from "@/components/runs/runs-table";

export default function RunsPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
        <p className="text-sm text-muted-foreground">Track planner and executor runs across agents.</p>
      </section>
      <RunsTable />
    </div>
  );
}

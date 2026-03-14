import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { OverviewMetrics } from "@/components/dashboard/overview-metrics";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Operational overview of your AI agent platform.</p>
      </section>
      <OverviewMetrics />
      <Card>
        <CardHeader>
          <CardTitle>Foundation Ready</CardTitle>
          <CardDescription>
            This dashboard is scaffolded for TanStack Query data hydration and modular feature expansion.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

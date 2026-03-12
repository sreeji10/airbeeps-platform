import { Activity, Bot, Database, MessageSquareText } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const metrics = [
  { label: "Active Agents", value: "12", icon: Bot, change: "+2 this week" },
  { label: "Chat Sessions", value: "348", icon: MessageSquareText, change: "+18 today" },
  { label: "Knowledge Sources", value: "29", icon: Database, change: "+4 this month" },
  { label: "Runtime Success", value: "97.8%", icon: Activity, change: "Stable" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Operational overview of your AI agent platform.</p>
      </section>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.label}>
              <CardHeader className="flex flex-row items-start justify-between space-y-0">
                <div>
                  <CardDescription>{metric.label}</CardDescription>
                  <CardTitle className="mt-2 text-2xl">{metric.value}</CardTitle>
                </div>
                <div className="rounded-md bg-secondary p-2 text-secondary-foreground">
                  <Icon className="h-4 w-4" />
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">{metric.change}</p>
              </CardContent>
            </Card>
          );
        })}
      </section>
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

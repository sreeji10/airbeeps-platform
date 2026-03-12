import { AgentsList } from "@/components/agents/agents-list";
import { CreateAgentForm } from "@/components/agents/create-agent-form";

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
        <p className="text-sm text-muted-foreground">Manage reusable agent configurations and defaults.</p>
      </section>
      <CreateAgentForm />
      <AgentsList />
    </div>
  );
}

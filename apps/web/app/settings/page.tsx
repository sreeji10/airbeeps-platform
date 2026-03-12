import { SettingsForm } from "@/components/settings-form";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Environment and workspace defaults for frontend connectivity.</p>
      </section>
      <SettingsForm />
    </div>
  );
}

import { SettingsForm } from "@/components/settings-form";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Environment configuration and context defaults. Authentication is managed from the sign-in flow.
        </p>
      </section>
      <SettingsForm />
    </div>
  );
}

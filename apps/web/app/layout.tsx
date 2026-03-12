import { AppShell } from "@/components/layout/app-shell";
import { AppSettingsBootstrap } from "@/components/providers/app-settings-bootstrap";
import { QueryProvider } from "@/components/providers/query-provider";

import "./globals.css";

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <AppSettingsBootstrap>
            <AppShell>{children}</AppShell>
          </AppSettingsBootstrap>
        </QueryProvider>
      </body>
    </html>
  );
}

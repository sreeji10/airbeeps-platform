import { AppShell } from "@/components/layout/app-shell";
import { AppSettingsBootstrap } from "@/components/providers/app-settings-bootstrap";
import { QueryProvider } from "@/components/providers/query-provider";
import { SessionBootstrap } from "@/components/providers/session-bootstrap";
import { Toaster } from "@/components/providers/toaster";

import "./globals.css";

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <AppSettingsBootstrap>
            <SessionBootstrap>
              <AppShell>{children}</AppShell>
              <Toaster />
            </SessionBootstrap>
          </AppSettingsBootstrap>
        </QueryProvider>
      </body>
    </html>
  );
}

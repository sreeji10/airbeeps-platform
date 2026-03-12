"use client";

import { useEffect } from "react";

import { clearAuthCookie, setAuthCookie } from "@/lib/auth";
import { useAppSettingsStore } from "@/store/app-settings-store";

type AppSettingsBootstrapProps = {
  children: React.ReactNode;
};

export function AppSettingsBootstrap({ children }: AppSettingsBootstrapProps) {
  const authToken = useAppSettingsStore((state) => state.authToken);

  useEffect(() => {
    if (authToken.trim()) {
      setAuthCookie(authToken.trim());
      return;
    }
    clearAuthCookie();
  }, [authToken]);

  return <>{children}</>;
}

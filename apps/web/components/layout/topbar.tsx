"use client";

import Link from "next/link";
import { Menu } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/store/ui-store";
import { useAppSettingsStore } from "@/store/app-settings-store";

export function Topbar() {
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);
  const workspaceId = useAppSettingsStore((state) => state.workspaceId);
  const projectId = useAppSettingsStore((state) => state.projectId);

  return (
    <header className="flex h-16 items-center gap-4 border-b border-border/70 bg-card/60 px-4 backdrop-blur-sm">
      <Button variant="ghost" size="icon" onClick={toggleSidebar} aria-label="Toggle sidebar">
        <Menu className="h-4 w-4" />
      </Button>
      <Input placeholder="Search agents, runs, knowledge..." className="max-w-md" />
      <div className="ml-auto flex items-center gap-2">
        <Badge className="border-primary/20 bg-primary/10 text-primary">{workspaceId}</Badge>
        <Badge className="border-border bg-muted text-foreground">{projectId}</Badge>
        <Link href="/settings" className={cn(buttonVariants({ variant: "outline" }))}>
          Context
        </Link>
      </div>
    </header>
  );
}

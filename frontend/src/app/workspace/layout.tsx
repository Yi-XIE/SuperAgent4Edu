"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCallback } from "react";
import { Toaster } from "sonner";

import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { WorkspaceSidebar } from "@/components/workspace/workspace-sidebar";
import { useLocalSettings } from "@/core/settings";

const queryClient = new QueryClient();

export default function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const [settings, setSettings] = useLocalSettings();
  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (settings.layout.sidebar_collapsed === !open) return;
      setSettings("layout", { sidebar_collapsed: !open });
    },
    [setSettings, settings.layout.sidebar_collapsed],
  );
  return (
    <QueryClientProvider client={queryClient}>
      <SidebarProvider
        className="h-screen"
        defaultOpen={!settings.layout.sidebar_collapsed}
        onOpenChange={handleOpenChange}
      >
        <WorkspaceSidebar />
        <SidebarInset className="min-w-0">{children}</SidebarInset>
      </SidebarProvider>
      <Toaster position="top-center" />
    </QueryClientProvider>
  );
}

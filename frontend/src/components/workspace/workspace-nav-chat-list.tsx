"use client";

import { BookOpenCheckIcon, HammerIcon, NetworkIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

export function WorkspaceNavChatList() {
  const pathname = usePathname();
  const isWorkflowActive = pathname.startsWith("/workspace/education/templates");
  const isEducationActive =
    pathname.startsWith("/workspace/education") && !isWorkflowActive;

  return (
    <SidebarGroup className="pt-1">
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton isActive={isEducationActive} asChild>
            <Link className="text-muted-foreground" href="/workspace/education">
              <BookOpenCheckIcon />
              <span>知识花园</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton isActive={isWorkflowActive} asChild>
            <Link
              className="text-muted-foreground"
              href="/workspace/education/templates"
            >
              <NetworkIcon />
              <span>智能体和工作流</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton
            isActive={pathname.startsWith("/workspace/agents")}
            asChild
          >
            <Link className="text-muted-foreground" href="/workspace/agents">
              <HammerIcon />
              <span>技能</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroup>
  );
}

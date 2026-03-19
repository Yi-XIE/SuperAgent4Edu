"use client";

import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";

export function EducationSectionShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <WorkspaceContainer>
      <WorkspaceHeader />
      <WorkspaceBody className="items-start p-6">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
          <Card>
            <CardHeader className="gap-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="text-base">{title}</CardTitle>
                  <p className="text-muted-foreground text-sm">{description}</p>
                </div>
                <Button asChild variant="outline">
                  <Link href="/workspace/education">
                    <ArrowLeftIcon className="h-4 w-4" />
                    返回教育 Hub
                  </Link>
                </Button>
              </div>
            </CardHeader>
          </Card>
          {children}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}

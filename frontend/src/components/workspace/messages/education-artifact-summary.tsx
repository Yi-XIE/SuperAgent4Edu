"use client";

import { ExternalLinkIcon, PackageOpenIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { urlOfArtifact } from "@/core/artifacts/utils";
import {
  parseCourseArtifactManifest,
  type CourseArtifactManifest,
} from "@/core/education";

export function EducationArtifactSummary({
  manifestPath,
  threadId,
}: {
  manifestPath: string;
  threadId: string;
}) {
  const [manifest, setManifest] = useState<CourseArtifactManifest | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadManifest() {
      try {
        const response = await fetch(
          urlOfArtifact({
            filepath: manifestPath,
            threadId,
          }),
        );
        if (!response.ok) {
          return;
        }

        const raw = (await response.json()) as unknown;
        const parsed = parseCourseArtifactManifest(raw);
        if (!cancelled) {
          setManifest(parsed);
        }
      } catch {
        if (!cancelled) {
          setManifest(null);
        }
      }
    }

    void loadManifest();

    return () => {
      cancelled = true;
    };
  }, [manifestPath, threadId]);

  if (!manifest) {
    return null;
  }

  return (
    <Card className="mb-4 w-full gap-4">
      <CardHeader className="gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 flex h-10 w-10 items-center justify-center rounded-full">
            <PackageOpenIcon className="text-primary h-5 w-5" />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-base">{manifest.title}</CardTitle>
            {manifest.summary && (
              <p className="text-muted-foreground text-sm">{manifest.summary}</p>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {manifest.artifacts
          .filter((artifact) => artifact.path !== manifestPath)
          .map((artifact) => (
            <a
              key={artifact.path}
              className="hover:border-primary/40 flex items-start justify-between gap-3 rounded-lg border p-3 transition-colors"
              href={urlOfArtifact({
                filepath: artifact.path,
                threadId,
              })}
              rel="noreferrer"
              target="_blank"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{artifact.label}</Badge>
                </div>
                {artifact.description && (
                  <p className="text-muted-foreground text-sm">
                    {artifact.description}
                  </p>
                )}
              </div>
              <ExternalLinkIcon className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
            </a>
          ))}
      </CardContent>
    </Card>
  );
}

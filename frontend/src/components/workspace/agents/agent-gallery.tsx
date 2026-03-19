"use client";

import { SparklesIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSkills } from "@/core/skills/hooks";

export function AgentGallery() {
  const { skills, isLoading } = useSkills();

  return (
    <div className="flex size-full flex-col">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div>
          <h1 className="text-xl font-semibold">技能</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">
            查看全部 Skills，按卡片浏览能力范围。
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="text-muted-foreground flex h-40 items-center justify-center text-sm">
            正在加载技能...
          </div>
        ) : skills.length === 0 ? (
          <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-lg border border-dashed text-center">
            <div className="bg-muted flex h-14 w-14 items-center justify-center rounded-full">
              <SparklesIcon className="text-muted-foreground h-7 w-7" />
            </div>
            <div>
              <p className="font-medium">当前没有可用技能</p>
              <p className="text-muted-foreground mt-1 text-sm">
                请检查后端技能配置或稍后重试。
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {skills.map((skill) => (
              <Card key={skill.name} className="flex h-full flex-col">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{skill.name}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col gap-3">
                  <p className="text-muted-foreground line-clamp-4 text-sm">
                    {skill.description}
                  </p>
                  <div className="mt-auto flex flex-wrap gap-2">
                    <Badge variant="outline">{skill.category}</Badge>
                    <Badge variant="outline">{skill.license}</Badge>
                    <Badge variant={skill.enabled ? "default" : "secondary"}>
                      {skill.enabled ? "已启用" : "未启用"}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

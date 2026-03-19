"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EducationSectionShell } from "@/components/workspace/education/education-section-shell";
import { useEducationWorkbench } from "@/core/education";

export default function EducationStudentsPage() {
  const { data } = useEducationWorkbench();

  return (
    <EducationSectionShell
      description="学生任务、提交与课堂反馈回流统一放在课后扩展页，不进入备课主舞台。"
      title="学生与反馈"
    >
      <Card>
        <CardHeader>
          <CardTitle className="text-base">学生任务</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.tasks.length === 0 && (
            <p className="text-muted-foreground text-sm">暂无学生任务</p>
          )}
          {data.tasks.map((task) => (
            <div key={task.id} className="rounded-lg border p-3">
              <p className="font-medium">{task.title}</p>
              <p className="text-muted-foreground mt-1 text-xs">
                run_id: {task.run_id} | 指派：{task.assigned_to.join(", ") || "-"}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">提交与教师反馈</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.submissions.map((submission) => (
            <div key={submission.id} className="rounded-lg border p-3">
              <p className="font-medium">
                {submission.student_user_id} {"->"} {submission.task_id}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                评分：{submission.score ?? "-"}
              </p>
            </div>
          ))}
          {data.feedback.map((item) => (
            <div key={item.id} className="rounded-lg border p-3">
              <p>{item.summary || "课堂反馈"}</p>
              <div className="mt-1 flex flex-wrap gap-2">
                <Badge variant="outline">
                  {item.source === "student_review" ? "学生评阅" : "手工反馈"}
                </Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </EducationSectionShell>
  );
}

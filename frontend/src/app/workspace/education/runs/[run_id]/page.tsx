import { EducationRunWorkbenchShell } from "@/components/workspace/education/education-run-workbench-shell";

export default async function EducationRunPage({
  params,
}: {
  params: Promise<{ run_id: string }>;
}) {
  const { run_id } = await params;
  return <EducationRunWorkbenchShell runId={run_id} />;
}

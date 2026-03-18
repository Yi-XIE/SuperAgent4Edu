#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[education-ci-quickcheck] backend contracts + state machine"
cd "$ROOT_DIR/backend"
if command -v uv >/dev/null 2>&1; then
  PYTEST_CMD=(uv run pytest)
else
  PYTEST_CMD=(python3 -m pytest)
fi
"${PYTEST_CMD[@]}" -p no:capture \
  tests/test_education_workflow_state_machine.py \
  tests/test_education_frontend_contracts.py \
  tests/test_education_docs_sync.py \
  tests/test_education_workflow_template_contract.py \
  tests/test_education_pre_retrieval_snapshot.py \
  tests/test_education_critic_auto_policy.py \
  tests/test_education_student_feedback_loop.py \
  tests/test_education_student_task_publish_guard.py \
  tests/test_education_run_result_objects.py \
  tests/test_education_run_thread_bootstrap.py \
  tests/test_education_task_tool_runtime_bridge.py

echo "[education-ci-quickcheck] frontend type contracts"
cd "$ROOT_DIR/frontend"
pnpm exec tsc --noEmit --incremental false

echo "[education-ci-quickcheck] done"

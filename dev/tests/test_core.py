import json
import os
import tempfile
import subprocess
import re
import unittest
from contextlib import redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import parse_qs
from unittest.mock import Mock, patch
from urllib.error import URLError

import yaml

from aipf.cli import main
from aipf.models import Kind
from aipf.notifications import NotificationResult, send_telegram, telegram_review_key, wait_for_review
from aipf.store import ProjectStore


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", *arguments), cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def initialize_git(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.name", "AIPF Test")
    git(root, "config", "user.email", "aipf@example.invalid")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "initial state")


def plan_spec() -> dict:
    return {
        "plan": {
            "goal": "Create a report",
            "roadmap_stage": "1. Create the report",
            "approach": ["Write the report from the requirements"],
            "risks": ["Requirements may be incomplete"],
            "scope": {"includes": ["report"], "excludes": []},
            "acceptance_criteria": ["The report exists"],
        },
        "tasks": [{
            "goal": "Write the report",
            "references": ["inputs/docs/requirements.md"],
            "outputs": ["src/report.md"],
            "constraints": ["Use the requirements"],
            "acceptance_criteria": ["src/report.md exists"],
            "verification": {"commands": [], "evidence": ["src/report.md"]},
        }],
    }


def parallel_plan_spec() -> dict:
    """Return two independent Tasks with disjoint declared output paths."""
    spec = plan_spec()
    task = spec["tasks"][0]
    spec["tasks"] = [
        task | {
            "id": "T_000",
            "goal": "Write the first report section",
            "outputs": ["src/report-a.md"],
            "acceptance_criteria": ["src/report-a.md exists"],
        },
        task | {
            "id": "T_001",
            "goal": "Write the second report section",
            "outputs": ["src/report-b.md"],
            "acceptance_criteria": ["src/report-b.md exists"],
        },
    ]
    return spec


def write_project_spec(root: Path) -> None:
    (root / "inputs" / "PROJECT_SPEC.md").write_text(
        "# Project specification\n\n## 7. 진행 계획\n\n1. Create the report\n",
        encoding="utf-8",
    )


def flow_section(root: Path) -> tuple[str, str, str]:
    """Return the generated flow body and its surrounding marker lines."""
    content = (root / "PROJECT_FLOW.md").read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    begin = next(
        index for index, line in enumerate(lines)
        if "AIPF" in line.upper() and ("START" in line.upper() or "BEGIN" in line.upper())
    )
    end = next(
        index for index, line in enumerate(lines[begin + 1:], begin + 1)
        if "AIPF" in line.upper() and "END" in line.upper()
    )
    return "".join(lines[begin + 1:end]), lines[begin], lines[end]


def flow_ids(body: str) -> set[str]:
    return set(re.findall(r"\b[APCET]_\d{3}(?:-C_\d{3})?\b", body))


def prepare_submitted_task(directory: str) -> ProjectStore:
    root = Path(directory)
    main(["--directory", directory, "init", "--goal", "Review project"])
    write_project_spec(root)
    (root / "inputs" / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    spec_path = root / "plan.yaml"
    spec_path.write_text(yaml.safe_dump(plan_spec(), sort_keys=False), encoding="utf-8")
    main(["--directory", directory, "plan", "apply", "--file", str(spec_path)])
    main(["--directory", directory, "review", "approve", "--target", "P_000"])
    main(["--directory", directory, "run"])
    (root / "src" / "report.md").write_text("# Report\n", encoding="utf-8")
    main([
        "--directory", directory, "task", "submit", "--target", "T_000",
        "--summary", "Report written", "--change", "Wrote src/report.md",
        "--evidence", "reviewed", "--output", "src/report.md",
    ])
    return ProjectStore(root)


def prepare_running_task(directory: str) -> ProjectStore:
    """Create the smallest project state that can receive a Telegram decision."""
    root = Path(directory)
    main(["--directory", directory, "init", "--goal", "Review project"])
    write_project_spec(root)
    (root / "inputs" / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    spec_path = root / "plan.yaml"
    spec_path.write_text(yaml.safe_dump(plan_spec(), sort_keys=False), encoding="utf-8")
    main(["--directory", directory, "plan", "apply", "--file", str(spec_path)])
    main(["--directory", directory, "review", "approve", "--target", "P_000"])
    main(["--directory", directory, "run"])
    return ProjectStore(root)


class TelegramResponse(BytesIO):
    """Minimal context-manager response accepted by urllib callers."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def telegram_response(payload: dict) -> TelegramResponse:
    return TelegramResponse(json.dumps(payload).encode("utf-8"))


def telegram_request_payload(request) -> dict:
    return {
        key: values[-1].decode("utf-8") if isinstance(values[-1], bytes) else values[-1]
        for key, values in parse_qs(request.data.decode("utf-8")).items()
    }


def telegram_state_snapshot(store: ProjectStore) -> dict[str, bytes]:
    """Capture persisted execution state to prove rejected waits are read-only."""
    paths = [
        store.runtime_path,
        store.root / "PROJECT.md",
        store.root / "PROJECT_FLOW.md",
        *store.paths(Kind.PLAN),
        *store.paths(Kind.TASK),
        *store.paths(Kind.EVIDENCE),
        *store.paths(Kind.AUDIT),
    ]
    return {str(path): path.read_bytes() for path in paths if path.exists()}


def callback_update(
    data: str,
    *,
    update_id: int = 1,
    chat_id: str = "chat-1",
    user_id: int = 7,
) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"callback-{update_id}",
            "from": {"id": user_id},
            "message": {"message_id": 10, "chat": {"id": chat_id, "type": "private"}},
            "data": data,
        },
    }


def text_update(
    text: str,
    *,
    update_id: int = 2,
    chat_id: str = "chat-1",
    user_id: int = 7,
) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 11,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": user_id},
            "text": text,
        },
    }


class CoreLifecycleTests(unittest.TestCase):
    def test_init_creates_visible_structure(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Test project"]), 0)
            root = Path(directory)
            for path in ("AGENTS.md", "SKILLS.md", "MEMORY_MAP.md", "README.md", "PROJECT.md", "PROJECT_FLOW.md", "inputs/PROJECT_SPEC.md", "inputs/docs", "inputs/codes", "inputs/data", "inputs/media", "ref", "src", ".aipf/plans", ".aipf/tasks", ".aipf/audits", ".aipf/evidence"):
                self.assertTrue((root / path).exists(), path)
            for object_directory in ("plans", "tasks", "audits", "evidence"):
                self.assertTrue((root / ".aipf" / object_directory / ".gitkeep").is_file(), object_directory)
            self.assertEqual(main(["--directory", directory, "validate"]), 0)

    def test_runtime_initializes_active_task_ids_and_reads_legacy_single_task_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Runtime compatibility"]), 0)
            store = ProjectStore(root)
            runtime = store.read(store.runtime_path)
            self.assertEqual(runtime.get("active_task_ids"), [])
            self.assertIsNone(runtime.get("active_task_id"))

            # Projects created before parallel execution have only active_task_id.
            legacy = dict(runtime)
            legacy.pop("active_task_ids")
            legacy["active_task_id"] = "T_000"
            store.write(store.runtime_path, legacy)
            self.assertEqual(main(["--directory", directory, "validate"]), 0)
            status = StringIO()
            with redirect_stdout(status):
                self.assertEqual(main(["--directory", directory, "status"]), 0)
            self.assertIn("task: T_000", status.getvalue())

    def test_parallel_independent_tasks_are_recorded_in_runtime_not_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Parallel execution"]), 0)
            write_project_spec(root)
            (root / "inputs" / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
            spec_path = root / "parallel.yaml"
            spec_path.write_text(yaml.safe_dump(parallel_plan_spec(), sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(spec_path)]), 0)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "P_000"]), 0)

            store = ProjectStore(root)
            plan_before = store.read_object(Kind.PLAN, "P_000")
            task_ids = plan_before["task_ids"]
            self.assertEqual(task_ids, ["T_000", "T_001"])
            self.assertEqual(main(["--directory", directory, "run", "--task", "T_000"]), 0)
            self.assertEqual(main(["--directory", directory, "run", "--task", "T_001"]), 0)

            self.assertEqual(main(["--directory", directory, "validate"]), 0)
            persisted = store.read(store.runtime_path)
            self.assertEqual(persisted["active_task_ids"], task_ids)
            self.assertEqual(persisted["active_task_id"], "T_000")
            self.assertEqual(store.read_object(Kind.PLAN, "P_000")["task_ids"], task_ids)

    def test_unpersisted_output_is_not_treated_as_verified_task_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = prepare_running_task(directory)
            (root / "src" / "report.md").write_text("output exists but is not yet verified\n", encoding="utf-8")
            before = store.read_object(Kind.TASK, "T_000")
            self.assertEqual(before["status"], "running")
            self.assertEqual(before["evidence_ids"], [])

            # A new session must reverify and submit the result; validation alone
            # must not infer completion from an unpersisted output file.
            self.assertEqual(main(["--directory", directory, "validate"]), 0)
            after = store.read_object(Kind.TASK, "T_000")
            self.assertEqual(after["status"], "running")
            self.assertEqual(after["evidence_ids"], [])

    def test_project_flow_initial_graph_is_deterministic_and_excludes_task_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Flow test"]), 0)
            flow = root / "PROJECT_FLOW.md"
            self.assertTrue(flow.is_file())
            initial = flow.read_text(encoding="utf-8")
            body, begin_marker, end_marker = flow_section(root)

            self.assertIn("flowchart", body)
            self.assertRegex(body, r"(?i)(current|status|awaiting_plan)")
            self.assertEqual(flow_ids(body) & {"T_000", "E_000"}, set())
            self.assertNotRegex(body, r"\b(?:T|E)_\d{3}\b")
            self.assertTrue(begin_marker.strip())
            self.assertTrue(end_marker.strip())

            self.assertEqual(main(["--directory", directory, "status"]), 0)
            self.assertEqual(flow.read_text(encoding="utf-8"), initial)

    def test_project_flow_contains_plan_checkpoint_audit_and_preserves_manual_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = prepare_submitted_task(directory)
            flow = root / "PROJECT_FLOW.md"
            original = flow.read_text(encoding="utf-8")
            _, begin_marker, end_marker = flow_section(root)
            begin_offset = original.index(begin_marker)
            end_offset = original.index(end_marker, begin_offset)
            prefix = original[:begin_offset]
            suffix = original[end_offset + len(end_marker):]
            flow.write_text(
                prefix + "<!-- user notes before generated graph -->\n" + begin_marker
                + original[begin_offset + len(begin_marker):end_offset] + end_marker
                + "<!-- user legend after generated graph -->\n" + suffix,
                encoding="utf-8",
            )

            self.assertEqual(main([
                "--directory", directory, "review", "approve", "--target", "T_000",
                "--audit-summary", "Accepted the report scope for the project",
            ]), 0)
            body, _, _ = flow_section(root)
            self.assertIn("P_000", body)
            self.assertIn("A_000", body)
            self.assertIn("Accepted the report scope for the project", body)
            self.assertNotRegex(body, r"\b(?:T|E)_\d{3}\b")
            refreshed = flow.read_text(encoding="utf-8")
            self.assertIn("<!-- user notes before generated graph -->", refreshed)
            self.assertIn("<!-- user legend after generated graph -->", refreshed)
            self.assertTrue(refreshed.startswith(prefix + "<!-- user notes before generated graph -->\n"))
            self.assertTrue(refreshed.endswith("<!-- user legend after generated graph -->\n" + suffix))

            initialize_git(root)
            (root / "src" / "report.md").write_text("checkpoint graph\n", encoding="utf-8")
            self.assertEqual(main([
                "--directory", directory, "checkpoint", "create", "--plan", "P_000",
                "--task", "T_000", "--path", "src/report.md",
            ]), 0)
            body, _, _ = flow_section(root)
            self.assertIn("P_000-C_001", body)
            self.assertNotRegex(body, r"\b(?:T|E)_\d{3}\b")

    def test_project_flow_rejects_damaged_markers_without_overwriting_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Marker test"]), 0)
            flow = root / "PROJECT_FLOW.md"
            content = flow.read_text(encoding="utf-8")
            _, _, end_marker = flow_section(root)
            damaged = content.replace(end_marker, "", 1)
            flow.write_text(damaged, encoding="utf-8")

            error = StringIO()
            with redirect_stdout(StringIO()), patch("sys.stderr", error):
                self.assertEqual(main(["--directory", directory, "status"]), 2)
            self.assertIn("marker", error.getvalue().lower())
            self.assertEqual(flow.read_text(encoding="utf-8"), damaged)

    def test_checkpoint_and_restore_commits_include_flow_and_restore_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = prepare_submitted_task(directory)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "T_000"]), 0)
            initialize_git(root)
            report = root / "src" / "report.md"
            report.write_text("flow checkpoint one\n", encoding="utf-8")
            create = [
                "--directory", directory, "checkpoint", "create", "--plan", "P_000",
                "--task", "T_000", "--path", "src/report.md",
            ]
            self.assertEqual(main(create), 0)
            first_commit = git(root, "rev-parse", "HEAD")
            first_changed = set(git(root, "show", "--format=", "--name-only", first_commit).splitlines())
            self.assertIn("PROJECT_FLOW.md", first_changed)

            flow = root / "PROJECT_FLOW.md"
            flow.write_text(flow.read_text(encoding="utf-8") + "\nUser legend retained across restore.\n", encoding="utf-8")
            report.write_text("flow checkpoint two\n", encoding="utf-8")
            self.assertEqual(main(create), 0)
            self.assertEqual(main([
                "--directory", directory, "checkpoint", "restore", "--target", "P_000-C_001",
                "--reason", "Restore the first flow checkpoint",
            ]), 0)
            restore_changed = set(git(root, "show", "--format=", "--name-only", "HEAD").splitlines())
            self.assertIn("PROJECT_FLOW.md", restore_changed)
            self.assertIn(".aipf/audits/A_000.yaml", restore_changed)
            body, _, _ = flow_section(root)
            self.assertIn("P_000-C_001", body)
            self.assertIn("A_000", body)
            self.assertIn("Restore the first flow checkpoint", body)
            self.assertNotRegex(body, r"\b(?:T|E)_\d{3}\b")
            self.assertIn("User legend retained across restore.", flow.read_text(encoding="utf-8"))
            self.assertEqual(list(store.objects(Kind.AUDIT))[-1]["event"], "checkpoint_restored")

    def test_init_generates_file_placement_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Layout test"]), 0)
            root = Path(directory)
            self.assertIn("Store implementation outputs under `src/`.", (root / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn(
                "AI-generated implementation and project deliverables belong under `src/`.",
                (root / "MEMORY_MAP.md").read_text(encoding="utf-8"),
            )
            self.assertIn("## 파일 생성 위치 규약", (root / "README.md").read_text(encoding="utf-8"))
            skills = (root / "SKILLS.md").read_text(encoding="utf-8")
            self.assertIn("Create only declared outputs under `src/`", skills)
            self.assertIn("Do not modify management objects or create Evidence", skills)
            self.assertIn("Routine accepted results need no user review or Audit", skills)
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("The Plan agent verifies each returned result", agents)
            self.assertRegex(agents, r"(?i)(routine result|routine acceptance)")
            self.assertRegex(agents, r"(?i)user review.*(needed|required|exception)")
            self.assertIn("- 경로: `inputs/docs/`", (root / "inputs" / "PROJECT_SPEC.md").read_text(encoding="utf-8"))

    def test_plan_apply_requires_project_spec_roadmap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Guard test"]), 0)
            plan_path = root / "plan.yaml"
            plan_path.write_text(yaml.safe_dump(plan_spec(), sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(plan_path)]), 2)
            (root / "inputs" / "PROJECT_SPEC.md").unlink()
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(plan_path)]), 2)
            write_project_spec(root)
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(plan_path)]), 0)

    def test_plan_apply_records_required_context_and_prints_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Report test"]), 0)
            write_project_spec(root)
            plan_path = root / "plan.yaml"
            plan_path.write_text(yaml.safe_dump(plan_spec(), sort_keys=False), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(plan_path)]), 0)

            plan = ProjectStore(root).read_object(Kind.PLAN, "P_000")
            self.assertEqual(plan["roadmap_stage"], "1. Create the report")
            self.assertEqual(plan["approach"], ["Write the report from the requirements"])
            self.assertEqual(plan["risks"], ["Requirements may be incomplete"])
            self.assertIsNone(plan["prior_plan_id"])
            self.assertEqual(plan["checkpoints"], [])
            report = output.getvalue()
            self.assertIn("Plan P_000 승인 전 보고", report)
            self.assertIn("Roadmap 단계: 1. Create the report", report)
            self.assertIn("수행 방법:", report)
            self.assertIn("위험 및 주의점:", report)
            self.assertIn("완료 조건:", report)

    def test_plan_apply_rejects_missing_required_report_fields(self):
        for field in ("roadmap_stage", "approach", "risks"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.assertEqual(main(["--directory", directory, "init", "--goal", "Plan validation"]), 0)
                write_project_spec(root)
                invalid = plan_spec()
                invalid["plan"].pop(field)
                plan_path = root / "plan.yaml"
                plan_path.write_text(yaml.safe_dump(invalid, sort_keys=False), encoding="utf-8")
                self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(plan_path)]), 2)

    def test_validate_checks_plan_checkpoint_structure(self):
        valid_checkpoint = {
            "id": "P_000-C_001",
            "task_ids": ["T_000"],
        }
        invalid_checkpoints = (
            "not-a-list",
            [{"id": "C_001", "task_ids": ["T_000"]}],
            [{"id": "P_000-C_001", "task_ids": ["not-a-task-id"]}],
            [{"id": "P_000-C_001", "task_ids": "T_000"}],
        )

        with tempfile.TemporaryDirectory() as directory:
            store = prepare_submitted_task(directory)
            plan = store.read_object(Kind.PLAN, "P_000")
            plan["checkpoints"] = [valid_checkpoint]
            store.write(store.path(Kind.PLAN, "P_000"), plan)
            self.assertEqual(main(["--directory", directory, "validate"]), 0)

        for invalid in invalid_checkpoints:
            with self.subTest(checkpoints=invalid), tempfile.TemporaryDirectory() as directory:
                store = prepare_submitted_task(directory)
                plan = store.read_object(Kind.PLAN, "P_000")
                plan["checkpoints"] = invalid
                store.write(store.path(Kind.PLAN, "P_000"), plan)
                self.assertEqual(main(["--directory", directory, "validate"]), 1)

    def test_checkpoint_commits_execution_and_indexes_multiple_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = prepare_submitted_task(directory)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "T_000"]), 0)
            initialize_git(root)
            (root / "src" / "report.md").write_text("# Revised report\n", encoding="utf-8")

            self.assertEqual(main([
                "--directory", directory, "checkpoint", "create",
                "--plan", "P_000", "--task", "T_000", "--path", "src/report.md",
            ]), 0)

            plan = store.read_object(Kind.PLAN, "P_000")
            self.assertEqual(plan["checkpoints"], [{"id": "P_000-C_001", "task_ids": ["T_000"]}])
            self.assertEqual(git(root, "log", "-1", "--format=%s"), "aipf(P_000-C_001): checkpoint T_000")
            self.assertEqual(git(root, "status", "--porcelain"), "")
            changed = set(git(root, "show", "--format=", "--name-only", "HEAD").splitlines())
            self.assertIn(".aipf/plans/P_000.yaml", changed)
            self.assertIn("src/report.md", changed)

    def test_checkpoint_rejects_unaccounted_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_submitted_task(directory)
            initialize_git(root)
            (root / "unexpected.txt").write_text("not part of the execution\n", encoding="utf-8")

            self.assertEqual(main([
                "--directory", directory, "checkpoint", "create",
                "--plan", "P_000", "--task", "T_000",
            ]), 2)
            self.assertEqual(ProjectStore(root).read_object(Kind.PLAN, "P_000")["checkpoints"], [])
            self.assertNotIn("P_000-C_001", git(root, "log", "--format=%s"))

    def test_checkpoint_restore_preserves_history_and_creates_audit_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = prepare_submitted_task(directory)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "T_000"]), 0)
            initialize_git(root)
            report = root / "src" / "report.md"
            report.write_text("checkpoint one\n", encoding="utf-8")
            create = [
                "--directory", directory, "checkpoint", "create",
                "--plan", "P_000", "--task", "T_000", "--path", "src/report.md",
            ]
            self.assertEqual(main(create), 0)
            first_commit = git(root, "rev-parse", "HEAD")
            report.write_text("checkpoint two\n", encoding="utf-8")
            self.assertEqual(main(create), 0)
            second_commit = git(root, "rev-parse", "HEAD")

            local_change = root / "local-note.txt"
            local_change.write_text("preserve me\n", encoding="utf-8")
            self.assertEqual(main([
                "--directory", directory, "checkpoint", "restore",
                "--target", "P_000-C_001", "--reason", "Must not overwrite local work",
            ]), 2)
            self.assertTrue(local_change.exists())
            self.assertEqual(len(list(store.objects(Kind.AUDIT))), 0)
            local_change.unlink()

            self.assertEqual(main([
                "--directory", directory, "checkpoint", "restore",
                "--target", "P_000-C_001", "--reason", "Second execution was incorrect",
            ]), 0)

            self.assertEqual(report.read_text(encoding="utf-8"), "checkpoint one\n")
            self.assertEqual(git(root, "merge-base", "--is-ancestor", first_commit, "HEAD"), "")
            self.assertEqual(git(root, "merge-base", "--is-ancestor", second_commit, "HEAD"), "")
            self.assertEqual(git(root, "log", "-1", "--format=%s"), "aipf(P_000-C_001): restore checkpoint")
            plan = store.read_object(Kind.PLAN, "P_000")
            self.assertEqual([item["id"] for item in plan["checkpoints"]], ["P_000-C_001", "P_000-C_002"])
            audit = list(store.objects(Kind.AUDIT))[-1]
            self.assertEqual(audit["event"], "checkpoint_restored")
            self.assertEqual(audit["target"], "P_000-C_001")
            self.assertEqual(audit["summary"], "Second execution was incorrect")
            self.assertEqual(main(["--directory", directory, "validate"]), 0)
            self.assertEqual(git(root, "status", "--porcelain"), "")

    def test_plan_task_review_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Draft"]), 0)
            write_project_spec(root)
            (root / "inputs" / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
            spec_path = root / "plan.yaml"
            spec_path.write_text(yaml.safe_dump(plan_spec(), sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(spec_path)]), 0)
            self.assertEqual(main(["--directory", directory, "run"]), 3)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "P_000"]), 0)
            self.assertEqual(main(["--directory", directory, "run"]), 0)
            (root / "src" / "report.md").write_text("# Report\n", encoding="utf-8")
            self.assertEqual(main([
                "--directory", directory, "task", "submit", "--target", "T_000",
                "--summary", "Report written", "--change", "Wrote src/report.md",
                "--evidence", "reviewed", "--output", "src/report.md",
            ]), 0)
            with patch("aipf.cli.notify", return_value=NotificationResult("failed", "network")):
                self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "T_000"]), 0)
            store = ProjectStore(root)
            self.assertEqual(store.read(store.runtime_path)["state"], "awaiting_plan_completion_confirmation")
            self.assertEqual(store.read_object(Kind.TASK, "T_000")["status"], "completed")
            self.assertEqual(store.read_object(Kind.PLAN, "P_000")["status"], "approved")
            self.assertEqual(len(store.paths(Kind.AUDIT)), 0)

            # A completed Task only produces a Plan completion report.  The
            # Plan remains open until the user explicitly confirms it.
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "P_000"]), 0)
            self.assertEqual(store.read(store.runtime_path)["state"], "awaiting_plan")
            self.assertEqual(store.read_object(Kind.PLAN, "P_000")["status"], "completed")

    def test_completed_plan_waits_for_new_session_and_new_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            store = prepare_submitted_task(directory)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "T_000"]), 0)
            runtime = store.read(store.runtime_path)
            self.assertEqual(runtime["state"], "awaiting_plan_completion_confirmation")
            self.assertEqual(runtime["active_plan_id"], "P_000")

            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "P_000"]), 0)
            self.assertEqual(store.read(store.runtime_path)["state"], "awaiting_plan")

            next_path = Path(directory) / "next.yaml"
            next_path.write_text(yaml.safe_dump(plan_spec(), sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(next_path)]), 0)
            self.assertEqual(store.read(store.runtime_path)["active_plan_id"], "P_001")
            self.assertEqual(store.read_object(Kind.PLAN, "P_000")["status"], "completed")
            self.assertEqual(store.read_object(Kind.PLAN, "P_001")["prior_plan_id"], "P_000")

    def test_project_completion_requires_user_command(self):
        with tempfile.TemporaryDirectory() as directory:
            store = prepare_submitted_task(directory)
            self.assertEqual(main(["--directory", directory, "project", "complete"]), 2)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "T_000"]), 0)
            self.assertEqual(main(["--directory", directory, "project", "complete"]), 2)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "P_000"]), 0)
            self.assertEqual(main(["--directory", directory, "project", "complete"]), 0)
            self.assertEqual(store.read(store.runtime_path)["state"], "completed")
            self.assertEqual(len(store.paths(Kind.AUDIT)), 1)
            self.assertEqual(list(store.objects(Kind.AUDIT))[-1]["event"], "project_completed")

    def test_user_can_revise_retry_or_cancel(self):
        expected = {"revise": "ready", "retry": "ready", "cancel": "cancelled"}
        for decision, state in expected.items():
            with self.subTest(decision=decision), tempfile.TemporaryDirectory() as directory:
                store = prepare_submitted_task(directory)
                arguments = ["--directory", directory, "review", decision, "--target", "T_000"]
                if decision == "revise":
                    arguments.extend(["--feedback", "Add more detail"])
                self.assertEqual(main(arguments), 0)
                task = store.read_object(Kind.TASK, "T_000")
                self.assertEqual(task["status"], state)
                self.assertEqual(len(store.paths(Kind.AUDIT)), 0)
                if decision == "revise":
                    self.assertEqual(task["feedback"], "Add more detail")

    def test_review_creates_audit_only_when_summary_is_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            store = prepare_submitted_task(directory)
            self.assertEqual(len(store.paths(Kind.AUDIT)), 0)
            self.assertEqual(main([
                "--directory", directory, "review", "approve", "--target", "T_000",
                "--audit-summary", "Accepted the submitted report as the project result",
            ]), 0)
            audits = list(store.objects(Kind.AUDIT))
            self.assertEqual(len(audits), 1)
            self.assertEqual(audits[0]["event"], "user_review")
            self.assertEqual(audits[0]["target"], "T_000")
            self.assertEqual(audits[0]["summary"], "Accepted the submitted report as the project result")
            self.assertEqual(audits[0]["decision"], "approve")

    def test_telegram_transport_is_optional_and_failure_safe(self):
        self.assertEqual(send_telegram("test", environ={}).status, "skipped")

        success = send_telegram(
            "test",
            environ={"AIPF_TELEGRAM_BOT_TOKEN": "token", "AIPF_TELEGRAM_CHAT_ID": "1"},
            opener=lambda request, timeout: TelegramResponse(b'{"ok": true}'),
        )
        self.assertEqual(success.status, "sent")

        failed = send_telegram(
            "test",
            environ={"AIPF_TELEGRAM_BOT_TOKEN": "token", "AIPF_TELEGRAM_CHAT_ID": "1"},
            opener=lambda request, timeout: (_ for _ in ()).throw(URLError("offline")),
        )
        self.assertEqual(failed.status, "failed")

    def test_run_uses_only_active_plan_task_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(main(["--directory", directory, "init", "--goal", "Order test"]), 0)
            write_project_spec(root)
            (root / "inputs" / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")

            first = plan_spec()
            first_path = root / "first.yaml"
            first_path.write_text(yaml.safe_dump(first, sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(first_path)]), 0)
            self.assertEqual(main([
                "--directory", directory, "review", "revise", "--target", "P_000", "--feedback", "Replace tasks",
            ]), 0)
            self.assertEqual(
                ProjectStore(root).read_object(Kind.PLAN, "P_000")["feedback"],
                "Replace tasks",
            )

            replacement = plan_spec()
            replacement["tasks"] = [
                plan_spec()["tasks"][0] | {"id": "T_005", "goal": "First declared task"},
                plan_spec()["tasks"][0] | {"id": "T_001", "goal": "Second declared task"},
            ]
            replacement_path = root / "replacement.yaml"
            replacement_path.write_text(yaml.safe_dump(replacement, sort_keys=False), encoding="utf-8")
            self.assertEqual(main(["--directory", directory, "plan", "apply", "--file", str(replacement_path)]), 0)
            self.assertEqual(main(["--directory", directory, "review", "approve", "--target", "P_000"]), 0)
            self.assertEqual(main(["--directory", directory, "run"]), 0)

            store = ProjectStore(root)
            runtime = store.read(store.runtime_path)
            self.assertEqual(runtime["active_task_id"], "T_005")
            self.assertEqual(runtime["active_task_ids"], ["T_005"])
            self.assertEqual(store.read_object(Kind.TASK, "T_000")["status"], "pending")

    def test_submit_requires_change_and_evidence_then_records_detailed_report(self):
        with tempfile.TemporaryDirectory() as directory:
            store = prepare_submitted_task(directory)
            task = store.read_object(Kind.TASK, "T_000")
            task["status"] = "running"
            store.write(store.path(Kind.TASK, "T_000"), task)

            without_change = [
                "--directory", directory, "task", "submit", "--target", "T_000", "--summary", "Draft result",
                "--evidence", "Manual verification completed",
            ]
            self.assertEqual(main(without_change), 2)

            without_evidence = [
                "--directory", directory, "task", "submit", "--target", "T_000", "--summary", "Draft result",
                "--change", "Drafted the report",
            ]
            self.assertEqual(main(without_evidence), 2)

            output = StringIO()
            with redirect_stdout(output):
                result = main(without_evidence + [
                    "--evidence", "Manual verification completed",
                    "--remaining", "Editorial review is still pending",
                    "--decision-needed", "Confirm the report tone",
                ])
            self.assertEqual(result, 0)
            self.assertIn("warning: declared outputs not submitted", output.getvalue())
            self.assertIn("Task T_000 완료 보고", output.getvalue())
            self.assertIn("실제 수행:", output.getvalue())
            self.assertIn("미완료 및 알려진 문제:", output.getvalue())
            self.assertIn("사용자 결정 필요:", output.getvalue())

            task = store.read_object(Kind.TASK, "T_000")
            self.assertNotIn("result", task)
            self.assertEqual(task["evidence_ids"], ["E_000", "E_001"])
            self.assertEqual(task["remaining"], ["Editorial review is still pending"])
            self.assertEqual(task["decisions"], ["Confirm the report tone"])
            evidence = store.read_object(Kind.EVIDENCE, "E_001")
            self.assertEqual(evidence["kind"], "evidence")
            self.assertEqual(evidence["plan_id"], "P_000")
            self.assertEqual(evidence["task_id"], "T_000")
            self.assertEqual(evidence["attempt"], 2)
            self.assertEqual(evidence["summary"], "Draft result")
            self.assertEqual(evidence["changes"], ["Drafted the report"])
            self.assertEqual(evidence["verification"], ["Manual verification completed"])
            self.assertEqual(evidence["outputs"], [])
            self.assertEqual(evidence["remaining"], ["Editorial review is still pending"])
            self.assertEqual(evidence["decisions"], ["Confirm the report tone"])
            project = (Path(directory) / "PROJECT.md").read_text(encoding="utf-8")
            self.assertIn("E_001", project)
            self.assertIn("Draft result", project)
            self.assertIn("Editorial review is still pending", project)
            self.assertIn("Confirm the report tone", project)

    def test_exceptional_task_result_stays_awaiting_plan_or_user_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = prepare_running_task(directory)
            (root / "src" / "report.md").write_text("# Report with follow-up\n", encoding="utf-8")
            self.assertEqual(main([
                "--directory", directory, "task", "submit", "--target", "T_000",
                "--summary", "Report written with an unresolved issue",
                "--plan-review",
                "--change", "Wrote src/report.md", "--evidence", "Checked the report",
                "--output", "src/report.md", "--remaining", "Editorial review is pending",
                "--decision-needed", "Choose the publication tone",
            ]), 0)

            task = store.read_object(Kind.TASK, "T_000")
            runtime = store.read(store.runtime_path)
            self.assertEqual(task["status"], "awaiting_review")
            self.assertEqual(runtime["state"], "awaiting_plan_task_review")
            self.assertEqual(task["review_stage"], "plan")
            self.assertEqual(task["remaining"], ["Editorial review is pending"])
            self.assertEqual(task["decisions"], ["Choose the publication tone"])
            self.assertEqual(task["evidence_ids"], ["E_000"])
            self.assertEqual(main([
                "--directory", directory, "task", "accept", "--target", "T_000", "--user-review",
            ]), 0)
            self.assertEqual(store.read(store.runtime_path)["state"], "awaiting_task_confirmation")
            self.assertEqual(store.read_object(Kind.TASK, "T_000")["review_stage"], "user")

    def test_plan_agent_accepts_routine_result_without_user_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = prepare_running_task(directory)
            (root / "src" / "report.md").write_text("# Verified report\n", encoding="utf-8")
            self.assertEqual(main([
                "--directory", directory, "task", "submit", "--target", "T_000", "--plan-review",
                "--summary", "Report written", "--change", "Wrote src/report.md",
                "--evidence", "All declared checks passed", "--output", "src/report.md",
            ]), 0)
            self.assertEqual(main([
                "--directory", directory, "task", "accept", "--target", "T_000",
            ]), 0)
            self.assertEqual(store.read_object(Kind.TASK, "T_000")["status"], "completed")
            self.assertEqual(len(store.paths(Kind.AUDIT)), 0)

    def test_task_resubmission_creates_new_evidence_and_preserves_history(self):
        for decision in ("revise", "retry"):
            with self.subTest(decision=decision), tempfile.TemporaryDirectory() as directory:
                store = prepare_submitted_task(directory)
                first = store.read_object(Kind.EVIDENCE, "E_000")
                arguments = ["--directory", directory, "review", decision, "--target", "T_000"]
                if decision == "revise":
                    arguments.extend(["--feedback", "Add more detail"])
                self.assertEqual(main(arguments), 0)
                self.assertEqual(main(["--directory", directory, "run"]), 0)
                self.assertEqual(main([
                    "--directory", directory, "task", "submit", "--target", "T_000",
                    "--summary", "Report revised", "--change", "Expanded src/report.md",
                    "--evidence", "Second verification completed", "--output", "src/report.md",
                ]), 0)

                task = store.read_object(Kind.TASK, "T_000")
                self.assertEqual(task["evidence_ids"], ["E_000", "E_001"])
                second = store.read_object(Kind.EVIDENCE, "E_001")
                self.assertEqual(second["attempt"], 2)
                self.assertEqual(second["summary"], "Report revised")
                self.assertEqual(second["verification"], ["Second verification completed"])
                self.assertEqual(store.read_object(Kind.EVIDENCE, "E_000"), first)
                project = (Path(directory) / "PROJECT.md").read_text(encoding="utf-8")
                self.assertIn("E_001", project)
                self.assertIn("Report revised", project)

    def test_validate_checks_evidence_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            store = prepare_submitted_task(directory)
            self.assertEqual(main(["--directory", directory, "validate"]), 0)
            store.path(Kind.EVIDENCE, "E_000").write_text(
                "id: E_000\nkind: evidence\n",
                encoding="utf-8",
            )
            self.assertEqual(main(["--directory", directory, "validate"]), 1)


class TelegramInteractionTests(unittest.TestCase):
    telegram_environment = {
        "AIPF_TELEGRAM_BOT_TOKEN": "test-token",
        "AIPF_TELEGRAM_CHAT_ID": "chat-1",
        "AIPF_TELEGRAM_USER_ID": "7",
    }

    def submit_task(self, directory: str, opener) -> ProjectStore:
        root = Path(directory)
        store = prepare_running_task(directory)
        (root / "src" / "report.md").write_text("# Report\n", encoding="utf-8")
        with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
            "aipf.notifications.urlopen", side_effect=opener,
        ):
            self.assertEqual(main([
                "--directory", directory, "task", "submit", "--target", "T_000",
                "--summary", "Report written", "--change", "Wrote src/report.md",
                "--evidence", "reviewed", "--output", "src/report.md",
            ]), 0)
        return store

    def test_review_required_sends_targeted_inline_keyboard_payload(self):
        requests = []
        key = telegram_review_key("T_000", "E_000")
        updates = [callback_update(f"aipf|approve|T_000|{key}")]

        def opener(request, timeout):
            requests.append((request, timeout))
            if "/getUpdates" in request.full_url:
                return telegram_response({"ok": True, "result": [updates.pop(0)]})
            return telegram_response({"ok": True, "result": {"message_id": 50}})

        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(directory, opener)
            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", side_effect=opener,
            ):
                self.assertEqual(main(["--directory", directory, "telegram", "wait"]), 0)
            self.assertEqual(store.read_object(Kind.TASK, "T_000")["status"], "completed")

        send_requests = [request for request, _ in requests if "/sendMessage" in request.full_url]
        review_requests = [request for request in send_requests if "reply_markup" in telegram_request_payload(request)]
        self.assertEqual(len(review_requests), 1)
        payload = telegram_request_payload(review_requests[0])
        self.assertEqual(payload["chat_id"], "chat-1")
        keyboard = json.loads(payload["reply_markup"])["inline_keyboard"]
        buttons = [button for row in keyboard for button in row]
        self.assertEqual(
            {button["callback_data"] for button in buttons},
            {
                f"aipf|approve|T_000|{key}", f"aipf|revise|T_000|{key}",
                f"aipf|retry|T_000|{key}", f"aipf|cancel|T_000|{key}",
                f"aipf|defer|T_000|{key}",
            },
        )

    def test_defer_ends_wait_without_mutating_review_state(self):
        key = telegram_review_key("T_000", "E_000")
        update = callback_update(f"aipf|defer|T_000|{key}")

        def opener(request, timeout):
            if "/getUpdates" in request.full_url:
                return telegram_response({"ok": True, "result": [update]})
            return telegram_response({"ok": True, "result": {}})

        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(directory, lambda request, timeout: telegram_response({"ok": True, "result": {}}))
            snapshot = telegram_state_snapshot(store)
            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", side_effect=opener,
            ):
                self.assertEqual(main(["--directory", directory, "telegram", "wait"]), 0)
            self.assertEqual(telegram_state_snapshot(store), snapshot)

    def test_authorized_approve_callback_changes_state_and_replay_is_read_only(self):
        key = telegram_review_key("T_000", "E_000")
        update = callback_update(f"aipf|approve|T_000|{key}")
        responses = [{"ok": True, "result": [update]}]

        def opener(request, timeout):
            if "/getUpdates" in request.full_url:
                return telegram_response(responses.pop(0) if responses else {"ok": True, "result": []})
            return telegram_response({"ok": True, "result": {}})

        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(directory, lambda request, timeout: telegram_response({"ok": True, "result": {}}))
            before = telegram_state_snapshot(store)
            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", side_effect=opener,
            ):
                self.assertEqual(main(["--directory", directory, "telegram", "wait"]), 0)
            self.assertEqual(store.read_object(Kind.TASK, "T_000")["status"], "completed")
            self.assertEqual(store.read(store.runtime_path)["state"], "awaiting_plan_completion_confirmation")
            self.assertNotEqual(before, telegram_state_snapshot(store))

            # A callback already consumed for T_000 is no longer a valid
            # decision after the Task has moved to completed.
            after_approval = telegram_state_snapshot(store)
            replay_clock = iter((0.0, 0.0, 601.0))
            result = wait_for_review(
                target="T_000", token="test-token", chat_id="chat-1", user_id="7",
                review_key="not-the-current-key", opener=lambda request, timeout: telegram_response(
                    {"ok": True, "result": [update]}
                ), clock=lambda: next(replay_clock), sleep_fn=lambda _: None,
            )
            self.assertEqual(result.status, "timeout")
            self.assertEqual(telegram_state_snapshot(store), after_approval)

    def test_plan_completion_confirmation_is_targeted_and_defer_is_read_only(self):
        task_key = telegram_review_key("T_000", "E_000")
        task_update = callback_update(f"aipf|approve|T_000|{task_key}", update_id=10)
        sent_payloads = []

        def approve_task_opener(request, timeout):
            if "/sendMessage" in request.full_url:
                sent_payloads.append(telegram_request_payload(request))
                return telegram_response({"ok": True, "result": {}})
            return telegram_response({"ok": True, "result": [task_update]})

        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(
                directory,
                lambda request, timeout: telegram_response({"ok": True, "result": {}}),
            )
            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", side_effect=approve_task_opener,
            ):
                self.assertEqual(main(["--directory", directory, "telegram", "wait"]), 0)

            self.assertEqual(store.read(store.runtime_path)["state"], "awaiting_plan_completion_confirmation")
            snapshot = telegram_state_snapshot(store)

            def defer_plan_opener(request, timeout):
                if "/sendMessage" in request.full_url:
                    sent_payloads.append(telegram_request_payload(request))
                    return telegram_response({"ok": True, "result": {}})
                payload = sent_payloads[-1]
                keyboard = json.loads(payload["reply_markup"])["inline_keyboard"]
                callbacks = [button["callback_data"] for row in keyboard for button in row]
                defer_callback = next(value for value in callbacks if value.startswith("aipf|defer|P_000|"))
                return telegram_response({
                    "ok": True,
                    "result": [callback_update(defer_callback, update_id=20)],
                })

            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", side_effect=defer_plan_opener,
            ):
                self.assertEqual(main(["--directory", directory, "telegram", "wait"]), 0)

            self.assertEqual(telegram_state_snapshot(store), snapshot)
            plan_review_messages = [
                payload for payload in sent_payloads
                if "reply_markup" in payload and "P_000" in payload["reply_markup"]
            ]
            self.assertEqual(len(plan_review_messages), 1)
            keyboard = json.loads(plan_review_messages[0]["reply_markup"])["inline_keyboard"]
            callbacks = [button["callback_data"] for row in keyboard for button in row]
            self.assertTrue(callbacks)
            self.assertTrue(all(callback.split("|")[2] == "P_000" for callback in callbacks))

    def test_unauthorized_chat_or_user_times_out_without_mutation(self):
        for field, value in (("chat", "other-chat"), ("user", 99)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                store = self.submit_task(directory, lambda request, timeout: telegram_response({"ok": True, "result": {}}))
                update = callback_update(
                    "aipf|approve|T_000",
                    chat_id=value if field == "chat" else "chat-1",
                    user_id=value if field == "user" else 7,
                )
                snapshot = telegram_state_snapshot(store)
                clock = iter((0.0, 0.0, 601.0))

                def opener(request, timeout):
                    if "/getUpdates" in request.full_url:
                        return telegram_response({"ok": True, "result": [update]})
                    return telegram_response({"ok": True, "result": {}})

                with patch.dict(os.environ, self.telegram_environment, clear=False):
                    result = wait_for_review(
                        target="T_000", token="test-token", chat_id="chat-1", user_id="7",
                        opener=opener, clock=lambda: next(clock), sleep_fn=lambda _: None,
                    )
                self.assertEqual(result.status, "timeout")
                self.assertEqual(telegram_state_snapshot(store), snapshot)

    def test_stale_or_wrong_target_callback_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(directory, lambda request, timeout: telegram_response({"ok": True, "result": {}}))
            snapshot = telegram_state_snapshot(store)
            update = callback_update("aipf|approve|T_000|stale-review")
            clock = iter((0.0, 0.0, 601.0))

            def opener(request, timeout):
                if "/getUpdates" in request.full_url:
                    return telegram_response({"ok": True, "result": [update]})
                return telegram_response({"ok": True, "result": {}})

            with patch.dict(os.environ, self.telegram_environment, clear=False):
                result = wait_for_review(
                    target="T_000", token="test-token", chat_id="chat-1", user_id="7",
                    review_key=telegram_review_key("T_000", "E_000"),
                    opener=opener, clock=lambda: next(clock), sleep_fn=lambda _: None,
                )
            self.assertEqual(result.status, "timeout")
            self.assertEqual(telegram_state_snapshot(store), snapshot)

    def test_wait_in_non_review_state_is_rejected_without_network_or_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = prepare_running_task(directory)
            snapshot = telegram_state_snapshot(store)
            opener = Mock(side_effect=AssertionError("Telegram must not be called"))
            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", opener,
            ):
                self.assertEqual(main(["--directory", directory, "telegram", "wait"]), 2)
            opener.assert_not_called()
            self.assertEqual(telegram_state_snapshot(store), snapshot)

    def test_project_transmission_condition_can_disable_task_review(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(directory, lambda request, timeout: telegram_response({"ok": True, "result": {}}))
            project_path = Path(directory) / "PROJECT.md"
            content = project_path.read_text(encoding="utf-8")
            content = re.sub(
                r"(?m)^- 전송 조건:.*$",
                "- 전송 조건: plan_review_required",
                content,
            )
            project_path.write_text(content, encoding="utf-8")
            snapshot = telegram_state_snapshot(store)
            opener = Mock(side_effect=AssertionError("Telegram must not be called"))
            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", opener,
            ):
                self.assertEqual(main(["--directory", directory, "telegram", "wait"]), 2)
            opener.assert_not_called()
            self.assertEqual(telegram_state_snapshot(store), snapshot)

    def test_revise_callback_then_feedback_message_updates_task_once(self):
        updates = [
            callback_update(
                f"aipf|revise|T_000|{telegram_review_key('T_000', 'E_000')}",
                update_id=20,
            ),
            text_update("Add more detail", update_id=21),
        ]

        def opener(request, timeout):
            if "/getUpdates" in request.full_url:
                return telegram_response({"ok": True, "result": [updates.pop(0)]})
            return telegram_response({"ok": True, "result": {}})

        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(directory, lambda request, timeout: telegram_response({"ok": True, "result": {}}))
            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", side_effect=opener,
            ):
                self.assertEqual(main(["--directory", directory, "telegram", "wait"]), 0)
            task = store.read_object(Kind.TASK, "T_000")
            self.assertEqual(task["status"], "ready")
            self.assertEqual(task["feedback"], "Add more detail")
            self.assertEqual(store.read(store.runtime_path)["state"], "ready")

    def test_default_wait_timeout_is_600_seconds_and_does_not_mutate_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(directory, lambda request, timeout: telegram_response({"ok": True, "result": {}}))
            snapshot = telegram_state_snapshot(store)
            calls = 0
            requests = []

            def clock():
                nonlocal calls
                calls += 1
                return 0.0 if calls <= 2 else 600.0

            def opener(request, timeout):
                requests.append((request, timeout))
                return telegram_response({"ok": True, "result": []})

            result = wait_for_review(
                target="T_000", token="test-token", chat_id="chat-1", user_id="7",
                opener=opener, clock=clock, sleep_fn=lambda _: None,
            )
            self.assertEqual(result.status, "timeout")
            self.assertTrue(any("/getUpdates" in request.full_url for request, _ in requests))
            self.assertEqual(telegram_state_snapshot(store), snapshot)

    def test_network_error_and_interrupt_leave_review_state_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.submit_task(directory, lambda request, timeout: telegram_response({"ok": True, "result": {}}))
            snapshot = telegram_state_snapshot(store)
            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", side_effect=URLError("offline"),
            ):
                self.assertNotEqual(main(["--directory", directory, "telegram", "wait"]), 0)
            self.assertEqual(telegram_state_snapshot(store), snapshot)

            with patch.dict(os.environ, self.telegram_environment, clear=False), patch(
                "aipf.notifications.urlopen", side_effect=KeyboardInterrupt,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    main(["--directory", directory, "telegram", "wait"])
            self.assertEqual(telegram_state_snapshot(store), snapshot)

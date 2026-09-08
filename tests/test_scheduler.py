import unittest

from aipf.models import ResourceClaim, Status, TaskView
from aipf.scheduler import claims_conflict, ready_batches


class SchedulerTests(unittest.TestCase):
    def test_writer_conflicts_with_reader(self):
        writer = ResourceClaim(write_set=("src",))
        reader = ResourceClaim(read_set=("src/app.py",))
        self.assertTrue(claims_conflict(writer, reader))

    def test_readers_do_not_conflict(self):
        left = ResourceClaim(read_set=("src/app.py",))
        right = ResourceClaim(read_set=("src/app.py",))
        self.assertFalse(claims_conflict(left, right))

    def test_batches_separate_conflicting_tasks(self):
        tasks = [
            TaskView("T_0000", "a", "first", Status.READY, claim=ResourceClaim(write_set=("src",))),
            TaskView("T_0001", "b", "second", Status.READY, claim=ResourceClaim(read_set=("src/x.py",))),
            TaskView("T_0002", "c", "third", Status.READY, claim=ResourceClaim(write_set=("docs",))),
        ]
        batches = ready_batches(tasks)
        self.assertEqual([[task.id for task in batch] for batch in batches], [["T_0000", "T_0002"], ["T_0001"]])

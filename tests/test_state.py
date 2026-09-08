import unittest

from aipf.models import Status
from aipf.state import InvalidTransition, validate_transition


class StateTests(unittest.TestCase):
    def test_happy_path(self):
        path = [
            Status.PENDING,
            Status.READY,
            Status.RUNNING,
            Status.REVIEW,
            Status.COMPLETED,
        ]
        for current, target in zip(path, path[1:]):
            validate_transition(current, target)

    def test_terminal_state_cannot_change(self):
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.COMPLETED, Status.RUNNING)

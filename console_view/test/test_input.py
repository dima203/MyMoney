import mock
import builtins

from console_view import ConsoleInput


class DisabledTestConsoleInput:
    def setup_class(self) -> None:
        self.input = ConsoleInput()

    def test_something(self):
        with mock.patch.object(builtins, "input", lambda _: "test input"):
            assert self.input.get_input() == "test input"

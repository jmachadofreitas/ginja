from collections.abc import Callable


class DocumentError(Exception):
    """A build failure, located by processing stage, source file and line where known."""

    def __init__(
        self, stage: str, message: str, path: str | None = None, line: int | None = None
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.path = path
        self.line = line

    def __str__(self) -> str:
        location = ""
        if self.path:
            location = f"{self.path}:{self.line}: " if self.line else f"{self.path}: "
        return f"[{self.stage}] {location}{self.message}"


def traceback_frames(error: BaseException, match: Callable[[str], bool]) -> list[tuple[str, int]]:
    """Return the traceback frames whose file name satisfies `match`, outermost first.

    Jinja rewrites tracebacks so that template code appears as frames whose file name is the
    template file and whose line is the template line, which makes this work for templates too.
    """

    frames = []
    frame = error.__traceback__
    while frame is not None:
        filename = frame.tb_frame.f_code.co_filename
        if match(filename) and (filename, frame.tb_lineno) not in frames[-1:]:
            frames.append((filename, frame.tb_lineno))
        frame = frame.tb_next
    return frames


def is_template_file(filename: str) -> bool:
    """Tell template frames apart from Python frames in a Jinja-rewritten traceback."""

    return not filename.endswith(".py") and not filename.startswith("<")

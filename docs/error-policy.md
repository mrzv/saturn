# Execution Error Policy

Saturn treats notebook execution errors differently depending on how execution was requested.

- Normal `saturn run` aborts on the first Python exception.
- Before re-raising the original exception, Saturn writes the processed notebook state when saving is enabled.
- The saved notebook includes the failing cell and any unprocessed incoming cells, so user code is not silently dropped.
- `SystemExit` is treated as a terminating signal. Saturn saves processed state and re-raises it with the original exit code.
- `KeyboardInterrupt` and other `BaseException` subclasses are treated as terminating signals. Saturn saves processed state and re-raises them.
- Forced execution mode records exception tracebacks as output cells and continues with later cells.
- REPL-entered cells use forced execution mode so an exception is captured in the notebook output instead of terminating the REPL session.
- Checkpoint and variable serialization failures are reported, but do not abort notebook execution.

This policy is covered by `tests/test_run_errors.py`.

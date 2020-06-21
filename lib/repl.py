from ptpython.repl import PythonRepl

class PythonReplWithExecute(PythonRepl):
    def __init__(self, execute, *args, **kw):
        self.execute__ = execute
        super().__init__(*args, **kw)

        # Swap enter and meta+enter #
        @self.add_key_binding('escape', 'enter')
        def _(event):
            event.current_buffer.insert_text('\n')

        @self.add_key_binding('enter', filter = self.show_exit_confirmation)
        def _(event):
            event.current_buffer.validate_and_handle()

    def _execute(self, line: str) -> None:
        self.execute__(line)



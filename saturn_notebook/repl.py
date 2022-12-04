from ptpython.repl import PythonRepl

class PythonReplWithExecute(PythonRepl):
    def __init__(self, execute, *args, **kw):
        self.execute__ = execute
        super().__init__(*args, **kw)

        self.show_meta_enter_message = False
        self.title = "Saturn "
        self.use_code_colorscheme('vim')

        self.complete_while_typing = False
        self.enable_history_search = True
        self.enable_auto_suggest = True

        # Swap enter and meta+enter #
        @self.add_key_binding('escape', 'enter')
        def _(event):
            event.current_buffer.insert_text('\n')

        @self.add_key_binding('enter', filter = self.show_exit_confirmation)
        def _(event):
            event.current_buffer.validate_and_handle()

    def eval(self, line: str) -> None:
        self.execute__(line)



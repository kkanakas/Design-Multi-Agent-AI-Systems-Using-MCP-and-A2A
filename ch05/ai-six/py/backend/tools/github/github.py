import shlex

from backend.tools.base.command_tool import CommandTool


class Github(CommandTool):
    def __init__(self, user: str | None = None):
        super().__init__(
            command_name='gh',
            user=user,
            doc_link='https://cli.github.com/manual/'
        )

    def run(self, **kwargs):
        args = shlex.split(kwargs['args'])

        if "--no-pager" not in args:
            args = ["--no-pager"] + args

        return super().run(args=' '.join(args))

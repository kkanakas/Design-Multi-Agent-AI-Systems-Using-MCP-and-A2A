import unittest
from unittest.mock import patch
from backend.tools.base import command_tool
from backend.tools.github.github import Github


class TestGithub(unittest.TestCase):

    @patch.object(command_tool, "sh")
    def test_run_gh_as_current_user(self, mock_sh):
        """gh runs under the current user with --no-pager injected."""
        github_tool = Github(user=None)
        github_tool.run(args="repo list")
        mock_sh.gh.assert_called_with("--no-pager", "repo", "list")

    @patch.object(command_tool, "sh")
    def test_run_gh_as_different_user(self, mock_sh):
        """gh runs via sudo when a user is specified."""
        github_tool = Github(user="other-user")
        github_tool.run(args="pr list")
        mock_sh.sudo.assert_called_with("-u", "other-user", "gh", "--no-pager", "pr", "list")

    @patch.object(command_tool, "sh")
    def test_no_pager_not_duplicated(self, mock_sh):
        """--no-pager is not injected twice if already present in args."""
        github_tool = Github(user=None)
        github_tool.run(args="--no-pager repo list")
        mock_sh.gh.assert_called_with("--no-pager", "repo", "list")

    @patch.object(command_tool, "sh")
    def test_run_issue_list(self, mock_sh):
        """gh can run issue list commands."""
        github_tool = Github(user=None)
        github_tool.run(args="issue list --repo owner/repo")
        mock_sh.gh.assert_called_with("--no-pager", "issue", "list", "--repo", "owner/repo")

    def test_tool_metadata(self):
        """Github tool has the correct name and description."""
        github_tool = Github()
        self.assertEqual(github_tool.name, "gh")
        self.assertIn("gh", github_tool.description)
        self.assertIn("https://cli.github.com/manual/", github_tool.description)

    def test_tool_parameters(self):
        """Github tool exposes a single 'args' parameter that is required."""
        github_tool = Github()
        self.assertEqual(len(github_tool.parameters), 1)
        self.assertEqual(github_tool.parameters[0].name, "args")
        self.assertIn("args", github_tool.required)


if __name__ == '__main__':
    unittest.main()

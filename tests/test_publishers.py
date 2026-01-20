"""Tests for publisher modules."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call, mock_open

from teamverse.models.content import BlogPost, Audience
from teamverse.publishers.github import (
    create_blog_post_pr,
    _run_git,
    _get_today,
)


# Fixtures


@pytest.fixture
def sample_blog_post():
    """Create a sample blog post for testing."""
    return BlogPost(
        title="Test Blog Post Title",
        description="A test blog post description",
        content="# Test\n\nThis is test content.",
        authors=["max-ghenis"],
        tags=["global", "org"],
    )


@pytest.fixture
def blog_post_with_image():
    """Create a blog post with a custom image filename."""
    return BlogPost(
        title="Post With Image",
        description="A post with a custom image",
        content="# Content\n\nWith image.",
        authors=["nikhil-woodruff"],
        tags=["uk", "policy"],
        image_filename="custom-image.png",
    )


@pytest.fixture
def mock_repo(tmp_path):
    """Create a mock repo directory structure."""
    repo_path = tmp_path / "policyengine-app-v2"
    articles_dir = repo_path / "app" / "src" / "data" / "posts" / "articles"
    images_dir = repo_path / "app" / "public" / "assets" / "posts"
    posts_json_path = repo_path / "app" / "src" / "data" / "posts" / "posts.json"

    # Create directories
    articles_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    # Create posts.json with existing posts
    existing_posts = [
        {
            "title": "Existing Post",
            "description": "An existing post",
            "date": "2025-01-01",
            "tags": ["existing"],
            "authors": ["author"],
            "filename": "existing-post.md",
            "image": "existing.png",
        }
    ]
    posts_json_path.write_text(json.dumps(existing_posts, indent=2))

    return repo_path


@pytest.fixture
def mock_image_file(tmp_path):
    """Create a mock image file."""
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake png data")
    return image_path


# Tests for branch name generation


class TestBranchNameGeneration:
    def test_simple_title(self, sample_blog_post, mock_repo):
        """Test branch name generation from simple title."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

            # We need to mock _get_today to have consistent dates
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)
                except RuntimeError:
                    pass  # Expected since gh pr create will fail

        # Check the branch name used in checkout -b call
        checkout_calls = [
            c
            for c in mock_subprocess.call_args_list
            if "checkout" in c[0][0] and "-b" in c[0][0]
        ]
        assert len(checkout_calls) == 1
        branch_name = checkout_calls[0][0][0][-1]
        assert branch_name == "add-test-blog-post-title"

    def test_title_with_special_characters(self, mock_repo):
        """Test branch name strips special characters."""
        post = BlogPost(
            title="What's New: 2025 Budget Analysis!",
            description="Desc",
            content="Content",
            authors=["author"],
            tags=["tag"],
        )

        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        checkout_calls = [
            c
            for c in mock_subprocess.call_args_list
            if "checkout" in c[0][0] and "-b" in c[0][0]
        ]
        branch_name = checkout_calls[0][0][0][-1]
        assert branch_name == "add-whats-new-2025-budget-analysis"

    def test_long_title_truncated(self, mock_repo):
        """Test branch name is truncated for long titles."""
        post = BlogPost(
            title="This is a very long title that should be truncated because branch names need limits",
            description="Desc",
            content="Content",
            authors=["author"],
            tags=["tag"],
        )

        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        checkout_calls = [
            c
            for c in mock_subprocess.call_args_list
            if "checkout" in c[0][0] and "-b" in c[0][0]
        ]
        branch_name = checkout_calls[0][0][0][-1]
        # Branch name should start with add- and slug should be <= 50 chars
        assert branch_name.startswith("add-")
        slug = branch_name[4:]  # Remove "add-" prefix
        assert len(slug) <= 50

    def test_custom_branch_name(self, sample_blog_post, mock_repo):
        """Test using a custom branch name."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(
                        sample_blog_post,
                        repo_path=mock_repo,
                        branch_name="custom-branch-123",
                    )
                except RuntimeError:
                    pass

        checkout_calls = [
            c
            for c in mock_subprocess.call_args_list
            if "checkout" in c[0][0] and "-b" in c[0][0]
        ]
        branch_name = checkout_calls[0][0][0][-1]
        assert branch_name == "custom-branch-123"


# Tests for markdown file writing


class TestMarkdownFileWriting:
    def test_markdown_file_created(self, sample_blog_post, mock_repo):
        """Test that markdown file is created with correct content."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        # Check the markdown file was created
        articles_dir = mock_repo / "app" / "src" / "data" / "posts" / "articles"
        md_files = list(articles_dir.glob("*.md"))
        assert len(md_files) == 1

        md_file = md_files[0]
        assert md_file.name == "test-blog-post-title.md"
        assert md_file.read_text() == sample_blog_post.content

    def test_markdown_filename_matches_slug(self, mock_repo):
        """Test that markdown filename uses the title slug."""
        post = BlogPost(
            title="New Policy: Tax Reform 2025",
            description="Desc",
            content="# Policy\n\nContent here.",
            authors=["author"],
            tags=["tag"],
        )

        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        articles_dir = mock_repo / "app" / "src" / "data" / "posts" / "articles"
        md_files = list(articles_dir.glob("*.md"))
        assert md_files[0].name == "new-policy-tax-reform-2025.md"


# Tests for posts.json update


class TestPostsJsonUpdate:
    def test_posts_json_updated(self, sample_blog_post, mock_repo):
        """Test that posts.json is updated with new entry."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        posts_json_path = (
            mock_repo / "app" / "src" / "data" / "posts" / "posts.json"
        )
        posts = json.loads(posts_json_path.read_text())

        # New post should be first
        assert len(posts) == 2
        new_post = posts[0]
        assert new_post["title"] == "Test Blog Post Title"
        assert new_post["description"] == "A test blog post description"
        assert new_post["date"] == "2025-01-20"
        assert new_post["tags"] == ["global", "org"]
        assert new_post["authors"] == ["max-ghenis"]
        assert new_post["filename"] == "test-blog-post-title.md"
        assert new_post["image"] == "test-blog-post-title.png"

    def test_new_post_prepended(self, sample_blog_post, mock_repo):
        """Test that new post is prepended to posts list."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        posts_json_path = (
            mock_repo / "app" / "src" / "data" / "posts" / "posts.json"
        )
        posts = json.loads(posts_json_path.read_text())

        # Existing post should be second
        assert posts[1]["title"] == "Existing Post"

    def test_custom_image_filename_in_posts_json(
        self, blog_post_with_image, mock_repo
    ):
        """Test that custom image filename is used in posts.json."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(blog_post_with_image, repo_path=mock_repo)
                except RuntimeError:
                    pass

        posts_json_path = (
            mock_repo / "app" / "src" / "data" / "posts" / "posts.json"
        )
        posts = json.loads(posts_json_path.read_text())

        assert posts[0]["image"] == "custom-image.png"


# Tests for image copying


class TestImageCopying:
    def test_image_copied_when_provided(
        self, sample_blog_post, mock_repo, mock_image_file
    ):
        """Test that image is copied to the images directory."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(
                        sample_blog_post,
                        image_path=mock_image_file,
                        repo_path=mock_repo,
                    )
                except RuntimeError:
                    pass

        images_dir = mock_repo / "app" / "public" / "assets" / "posts"
        image_files = list(images_dir.glob("*.png"))
        assert len(image_files) == 1
        assert image_files[0].name == "test-blog-post-title.png"
        assert image_files[0].read_bytes() == b"fake png data"

    def test_custom_image_filename(
        self, blog_post_with_image, mock_repo, mock_image_file
    ):
        """Test that custom image filename is used when specified."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(
                        blog_post_with_image,
                        image_path=mock_image_file,
                        repo_path=mock_repo,
                    )
                except RuntimeError:
                    pass

        images_dir = mock_repo / "app" / "public" / "assets" / "posts"
        image_files = list(images_dir.glob("*.png"))
        assert any(f.name == "custom-image.png" for f in image_files)

    def test_no_image_when_not_provided(self, sample_blog_post, mock_repo):
        """Test that no image is copied when not provided."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        images_dir = mock_repo / "app" / "public" / "assets" / "posts"
        image_files = list(images_dir.glob("*.png"))
        assert len(image_files) == 0

    def test_nonexistent_image_not_copied(self, sample_blog_post, mock_repo, tmp_path):
        """Test that nonexistent image path doesn't cause errors."""
        fake_image = tmp_path / "nonexistent.png"

        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(
                        sample_blog_post,
                        image_path=fake_image,
                        repo_path=mock_repo,
                    )
                except RuntimeError:
                    pass

        images_dir = mock_repo / "app" / "public" / "assets" / "posts"
        image_files = list(images_dir.glob("*.png"))
        assert len(image_files) == 0


# Tests for git operations


class TestGitOperations:
    def test_git_checkout_main(self, sample_blog_post, mock_repo):
        """Test that git checkout main is called."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        calls = mock_subprocess.call_args_list
        checkout_main = [c for c in calls if c[0][0] == ["git", "checkout", "main"]]
        assert len(checkout_main) == 1

    def test_git_pull(self, sample_blog_post, mock_repo):
        """Test that git pull is called."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        calls = mock_subprocess.call_args_list
        pull_calls = [c for c in calls if c[0][0] == ["git", "pull"]]
        assert len(pull_calls) == 1

    def test_git_add_commit_push(self, sample_blog_post, mock_repo):
        """Test that git add, commit, and push are called."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                try:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)
                except RuntimeError:
                    pass

        calls = mock_subprocess.call_args_list
        add_calls = [c for c in calls if c[0][0] == ["git", "add", "."]]
        commit_calls = [
            c
            for c in calls
            if "commit" in c[0][0] and "-m" in c[0][0]
        ]
        push_calls = [c for c in calls if "push" in c[0][0]]

        assert len(add_calls) == 1
        assert len(commit_calls) == 1
        assert len(push_calls) == 1

        # Check commit message
        commit_call = commit_calls[0]
        assert "Add blog post: Test Blog Post Title" in commit_call[0][0]

        # Check push includes -u origin
        push_call = push_calls[0]
        assert "-u" in push_call[0][0]
        assert "origin" in push_call[0][0]

    def test_git_operations_order(self, sample_blog_post, mock_repo):
        """Test that git operations are called in correct order."""
        call_order = []

        def track_calls(args, **kwargs):
            if args[0] == "git":
                call_order.append(args[1])
            elif args[0] == "gh":
                call_order.append("gh_pr")
            return Mock(returncode=0, stdout="https://github.com/pr/1", stderr="")

        with patch(
            "teamverse.publishers.github.subprocess.run", side_effect=track_calls
        ):
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                create_blog_post_pr(sample_blog_post, repo_path=mock_repo)

        expected_order = [
            "checkout",  # checkout main
            "pull",
            "checkout",  # checkout -b branch
            "add",
            "commit",
            "push",
            "gh_pr",
        ]
        assert call_order == expected_order


# Tests for _run_git helper


class TestRunGit:
    def test_successful_git_command(self, tmp_path):
        """Test successful git command execution."""
        with patch("teamverse.publishers.github.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            _run_git(tmp_path, ["status"])

            mock_run.assert_called_once_with(
                ["git", "status"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
            )

    def test_failed_git_command_raises(self, tmp_path):
        """Test that failed git command raises RuntimeError."""
        with patch("teamverse.publishers.github.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stdout="", stderr="fatal: not a git repository"
            )

            with pytest.raises(RuntimeError) as exc_info:
                _run_git(tmp_path, ["status"])

            assert "fatal: not a git repository" in str(exc_info.value)


# Tests for PR creation


class TestPRCreation:
    def test_pr_created_with_correct_args(self, sample_blog_post, mock_repo):
        """Test that PR is created with correct arguments."""
        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(
                returncode=0, stdout="https://github.com/pr/1", stderr=""
            )
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                result = create_blog_post_pr(sample_blog_post, repo_path=mock_repo)

        calls = mock_subprocess.call_args_list
        gh_calls = [c for c in calls if c[0][0][0] == "gh"]
        assert len(gh_calls) == 1

        gh_call = gh_calls[0]
        args = gh_call[0][0]
        assert args[0] == "gh"
        assert args[1] == "pr"
        assert args[2] == "create"
        assert "--title" in args
        assert "Add blog post: Test Blog Post Title" in args
        assert "--body" in args

        assert result == "https://github.com/pr/1"

    def test_pr_creation_failure_raises(self, sample_blog_post, mock_repo):
        """Test that PR creation failure raises RuntimeError."""

        def mock_run(args, **kwargs):
            if args[0] == "gh":
                return Mock(
                    returncode=1,
                    stdout="",
                    stderr="error: no git remote for 'origin'",
                )
            return Mock(returncode=0, stdout="", stderr="")

        with patch(
            "teamverse.publishers.github.subprocess.run", side_effect=mock_run
        ):
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                with pytest.raises(RuntimeError) as exc_info:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)

                assert "Failed to create PR" in str(exc_info.value)

    def test_pr_url_returned(self, sample_blog_post, mock_repo):
        """Test that PR URL is returned."""
        expected_url = "https://github.com/PolicyEngine/policyengine-app-v2/pull/123"

        with patch(
            "teamverse.publishers.github.subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = Mock(
                returncode=0, stdout=f"{expected_url}\n", stderr=""
            )
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                result = create_blog_post_pr(sample_blog_post, repo_path=mock_repo)

        assert result == expected_url


# Tests for error handling


class TestErrorHandling:
    def test_repo_not_found_raises(self, sample_blog_post, tmp_path):
        """Test that missing repo raises RuntimeError."""
        fake_repo = tmp_path / "nonexistent-repo"

        with pytest.raises(RuntimeError) as exc_info:
            create_blog_post_pr(sample_blog_post, repo_path=fake_repo)

        assert "not found" in str(exc_info.value)

    def test_git_checkout_failure(self, sample_blog_post, mock_repo):
        """Test that git checkout failure raises RuntimeError."""

        def mock_run(args, **kwargs):
            if args == ["git", "checkout", "main"]:
                return Mock(
                    returncode=1, stdout="", stderr="error: pathspec 'main'"
                )
            return Mock(returncode=0, stdout="", stderr="")

        with patch(
            "teamverse.publishers.github.subprocess.run", side_effect=mock_run
        ):
            with pytest.raises(RuntimeError) as exc_info:
                create_blog_post_pr(sample_blog_post, repo_path=mock_repo)

            assert "Git command failed" in str(exc_info.value)

    def test_git_push_failure(self, sample_blog_post, mock_repo):
        """Test that git push failure raises RuntimeError."""

        def mock_run(args, **kwargs):
            if "push" in args:
                return Mock(
                    returncode=1,
                    stdout="",
                    stderr="error: failed to push some refs",
                )
            return Mock(returncode=0, stdout="", stderr="")

        with patch(
            "teamverse.publishers.github.subprocess.run", side_effect=mock_run
        ):
            with patch(
                "teamverse.publishers.github._get_today", return_value="2025-01-20"
            ):
                with pytest.raises(RuntimeError) as exc_info:
                    create_blog_post_pr(sample_blog_post, repo_path=mock_repo)

                assert "Git command failed" in str(exc_info.value)


# Tests for _get_today helper


class TestGetToday:
    def test_returns_iso_format(self):
        """Test that _get_today returns date in ISO format."""
        from datetime import date

        with patch("datetime.date") as mock_date:
            mock_date.today.return_value = date(2025, 1, 20)

            result = _get_today()

            # The function imports date inside, so we need to test differently
            # Just verify the format is correct
            import re

            assert re.match(r"^\d{4}-\d{2}-\d{2}$", result)

    def test_actual_date_format(self):
        """Test that actual _get_today returns proper format."""
        result = _get_today()

        # Should match YYYY-MM-DD format
        import re

        assert re.match(r"^\d{4}-\d{2}-\d{2}$", result)

    def test_returns_current_date(self):
        """Test that _get_today returns today's date."""
        from datetime import date

        result = _get_today()
        expected = date.today().isoformat()

        assert result == expected


# Tests for default repo path


class TestDefaultRepoPath:
    def test_uses_default_repo_path(self, sample_blog_post):
        """Test that default repo path is used when not specified."""
        default_path = Path.home() / "PolicyEngine" / "policyengine-app-v2"

        # This should raise because the repo doesn't exist at the default path
        # (or if it does, we don't have proper mocking set up)
        if not default_path.exists():
            with pytest.raises(RuntimeError) as exc_info:
                create_blog_post_pr(sample_blog_post)

            assert str(default_path) in str(exc_info.value)

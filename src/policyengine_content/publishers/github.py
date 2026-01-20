"""GitHub publisher for creating PRs to app-v2."""

import json
import subprocess
from pathlib import Path
from typing import Optional

from policyengine_content.models.content import BlogPost, Audience


def create_blog_post_pr(
    post: BlogPost,
    image_path: Optional[Path] = None,
    repo_path: Optional[Path] = None,
    branch_name: Optional[str] = None,
) -> str:
    """Create a PR to policyengine-app-v2 with a blog post.

    Args:
        post: BlogPost model with content
        image_path: Optional path to social image
        repo_path: Path to local app-v2 repo (default: ~/PolicyEngine/policyengine-app-v2)
        branch_name: Branch name for the PR (default: auto-generated from title)

    Returns:
        URL of the created PR

    Raises:
        RuntimeError: If git operations fail
    """
    if repo_path is None:
        repo_path = Path.home() / "PolicyEngine" / "policyengine-app-v2"

    if not repo_path.exists():
        raise RuntimeError(f"App-v2 repo not found at {repo_path}")

    # Generate slug from title (always needed for filename)
    slug = post.title.lower()
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    slug = "-".join(slug.split())[:50]

    # Generate branch name from title if not provided
    if branch_name is None:
        branch_name = f"add-{slug}"

    # Create branch
    _run_git(repo_path, ["checkout", "main"])
    _run_git(repo_path, ["pull"])
    _run_git(repo_path, ["checkout", "-b", branch_name])

    # Write blog post markdown
    articles_dir = repo_path / "app" / "src" / "data" / "posts" / "articles"
    filename = f"{slug}.md"
    post_path = articles_dir / filename
    post_path.write_text(post.content)

    # Copy image if provided
    if image_path and image_path.exists():
        images_dir = repo_path / "app" / "public" / "assets" / "posts"
        image_dest = images_dir / (post.image_filename or f"{slug}.png")
        import shutil
        shutil.copy(image_path, image_dest)

    # Update posts.json
    posts_json_path = repo_path / "app" / "src" / "data" / "posts" / "posts.json"
    with open(posts_json_path) as f:
        posts = json.load(f)

    new_entry = {
        "title": post.title,
        "description": post.description,
        "date": _get_today(),
        "tags": post.tags,
        "authors": post.authors,
        "filename": filename,
        "image": post.image_filename or f"{slug}.png",
    }
    posts.insert(0, new_entry)

    with open(posts_json_path, "w") as f:
        json.dump(posts, f, indent=2)

    # Commit and push
    _run_git(repo_path, ["add", "."])
    _run_git(repo_path, ["commit", "-m", f"Add blog post: {post.title}"])
    _run_git(repo_path, ["push", "-u", "origin", branch_name])

    # Create PR
    result = subprocess.run(
        [
            "gh", "pr", "create",
            "--title", f"Add blog post: {post.title}",
            "--body", f"## Summary\n\nAdds blog post: {post.title}\n\n{post.description}",
        ],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create PR: {result.stderr}")

    return result.stdout.strip()


def _run_git(repo_path: Path, args: list[str]) -> None:
    """Run a git command in the repo."""
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {result.stderr}")


def _get_today() -> str:
    """Get today's date in YYYY-MM-DD format."""
    from datetime import date
    return date.today().isoformat()

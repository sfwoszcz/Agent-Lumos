# Publish Agent Lumos v1.2.0 to GitHub

This guide assumes a **new GitHub repository** named `agent-lumos`. Run commands from the extracted project's root directory (the folder containing `pyproject.toml`). Do not publish `.env`, private keys, device credentials or generated build files.

## Option A: GitHub CLI (recommended)

Install Git, the [GitHub CLI](https://cli.github.com/) and authenticate:

```bash
gh auth login
gh auth status
```

Set Git identity if your machine does not already have it:

```bash
git config --global user.name "YOUR NAME"
git config --global user.email "YOUR VERIFIED EMAIL"
```

Verify you are at the project root, and inspect what will be published:

```bash
git init -b main
git add .
git status --short
```

**Review the staged files**. If you see `.env`, private keys or sensitive data, STOP and remove them before continuing.

Commit the source and create an annotated release tag:

```bash
git commit -m "Release Agent Lumos v1.2.0"
git tag -a v1.2.0 -m "Agent Lumos v1.2.0"
```

Create the public repository, push your main branch, and publish the tag:

```bash
gh repo create agent-lumos --public --source=. --remote=origin --push
git push origin v1.2.0
```

Publish a GitHub Release with the prepared release notes:

```bash
gh release create v1.2.0 \
  --title "Agent Lumos v1.2.0" \
  --notes-file RELEASE_NOTES_v1.2.0.md
```

Check the repository and release in your browser:

```bash
gh repo view --web
gh release view v1.2.0 --web
```

**If the repository already exists:** do not run `gh repo create`. Instead attach the existing remote using `git remote add origin https://github.com/YOUR-USERNAME/agent-lumos.git` (if no `origin` exists), then `git push -u origin main` and `git push origin v1.2.0`. Resolve any unrelated remote history before pushing; never force-push blindly.

## Option B: GitHub web interface + Git

1. Log in to GitHub and create a **new empty public repository** named `agent-lumos`, without initializing a README, .gitignore or license.
2. Run the `git init`, `git add`, `git commit` and `git tag` commands from Option A.
3. Add your repository remote and push:
   ```bash
   git remote add origin https://github.com/YOUR-USERNAME/agent-lumos.git
   git push -u origin main
   git push origin v1.2.0
   ```
4. Open your repository's **Releases** area and choose **Draft a new release**.
5. Select tag `v1.2.0`, set title `Agent Lumos v1.2.0`, paste the content of `RELEASE_NOTES_v1.2.0.md`, and publish.

GitHub automatically provides source archives for a GitHub Release. You do not have to upload the original ZIP file as an extra asset.

## After publishing

- Confirm GitHub Actions tests have run and review failures if any.
- Set the repository description and topics (`python`, `embedded-systems`, `stm32`, `cpp`, `cmake`, `cybersecurity`, `machine-learning`).
- Consider pinning the repository on your GitHub profile.
- Never commit `.env`, tokens, passwords or private keys.

## Troubleshooting

- `gh: command not found`: install the GitHub CLI, or use Option B.
- `Author identity unknown`: configure `git config user.name` and `git config user.email`.
- `Repository already exists`: use the existing-repository path; do not overwrite history.
- `remote origin already exists`: inspect `git remote -v` rather than adding it twice.
- `tag already exists`: inspect `git tag -n` before creating another.
- HTTPS push prompts for credentials: use `gh auth login` or configure a Git credential helper; GitHub password-based Git authentication is not supported.

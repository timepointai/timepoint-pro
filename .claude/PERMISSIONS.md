# Setup Permissions in Claude

```bash
/permissions allow bash(pytest *)
/permissions allow bash(python *)
/permissions allow bash(uv *)
/permissions allow bash(ruff *)
/permissions allow bash(mypy *)
/permissions allow bash(git status)
/permissions allow bash(git diff *)
/permissions allow bash(git add *)
/permissions allow bash(git commit *)
/permissions allow bash(docker *)
```

Or: `claude --dangerously-skip-permissions`

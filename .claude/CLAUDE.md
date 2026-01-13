# Claude Code Safety Instructions

## Before Making Major Changes

1. **Create a checkpoint commit** before any significant refactoring or multi-file changes:
   ```bash
   git add -A && git commit -m "checkpoint: before [description]"
   ```

2. **Update PLAN.md** with your current task status

## Never Do

- **Never modify** `.env`, `.env.*`, or any file with "secret" in the name
- **Never write** to `config/prod/` directory
- **Never run** `rm -rf`, `sudo`, or destructive commands
- **Never push** to remote without explicit user approval
- **Never commit** without explicit user approval

## Always Do

- **Ask before deleting** any files - use `git rm` for tracked files
- **Update PLAN.md** status after completing each task
- **Run tests** after making changes: `pytest` or `npm test`
- **Check for errors** before considering a task complete

## Safe Workflow

1. Read and understand the current code first
2. Create a checkpoint if making significant changes
3. Make incremental changes
4. Test after each change
5. Update PLAN.md with progress

## Recovery

If something goes wrong, run:
```bash
./scripts/claude-reset.sh
```

This will restore the working directory to the last commit.

# Remote Repository Initialization

Target: `woshixiong/trader-assist-v0`

The remote repository must be created as private and empty. Do not initialize it with a README, license, or `.gitignore`, because the bootstrap history already contains the reviewed base commit.

From the local bootstrap repository:

```bash
gh repo create woshixiong/trader-assist-v0 --private --source . --remote origin
git push -u origin main
git push -u origin feature/v0-00-bootstrap-contracts
gh pr create \
  --base main \
  --head feature/v0-00-bootstrap-contracts \
  --title "feat: freeze V0 bootstrap contracts and governance" \
  --body-file docs/V0_00_PR_BODY.md
```

Do not merge the pull request until CI and an independent review pass.

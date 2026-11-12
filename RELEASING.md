# Releasing ONE-PIX

## Before tagging

1. `python -m pytest test` passes, and the GitHub Actions workflow is green on the commit to release.
2. Set the version in `pyproject.toml` (the only place: the documentation reads it from there).
3. In `CITATION.cff`, set `version` and `date-released` to the release.
4. In `CHANGELOG.md`, replace `unreleased` in the heading by the date, and check each entry against
   the code: only what is in this release.
5. Plugins the release depends on (`onepix-*`, `analysis-pipeline`, `basic-treatments`) are published
   in versions that work with it; note any version that is required in the changelog.

## Publish

```bash
git tag -a vX.Y.Z -m "ONE-PIX X.Y.Z"
git push github vX.Y.Z
```

Create the GitHub Release from the tag, with the changelog entry as notes. ONE-PIX is installed from a
clone of the repository (the pip package holds only `onepix/`, not `conf/` or `app/`) and is not
published to PyPI.

## Going back

Never rewrite a published branch. Before merging a major version into `main`, tag what `main` is
(`git tag vX.Y.Z-last main`); to go back, either revert the merge
(`git revert -m 1 <merge commit>`) or check out that tag. A machine that runs the service goes back
with `git checkout <tag>` in its clone, then `sudo systemctl restart onepix` (or `onepix_app`).
`measure/` is not tracked, so an update never touches the measurements. `conf/hardware_config.json` and
`conf/acquisition_parameters.json` are tracked: a machine with its own values updates with
`git pull --rebase --autostash` (or `git stash` first) and checks them afterwards.

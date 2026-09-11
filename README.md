# AIPF

AIPF is a file-based framework for user-controlled AI projects. This branch is
the installable distribution; development sources and the generated example
are maintained on the `main` branch.

## Requirements

- Python 3.12 or newer
- Git when using AIPF checkpoints

## Install from the release branch

```bash
git clone --branch release --single-branch \
  git@github.com:yuyu0830/aipf.git ~/tools/aipf
python3.12 -m venv ~/tools/aipf/.venv
~/tools/aipf/.venv/bin/python -m pip install ~/tools/aipf
```

## Create a project

```bash
~/tools/aipf/.venv/bin/aipf \
  --directory ~/projects/my-project \
  init \
  --goal "프로젝트 목표"
```

Initialize Git and create the first commit before using checkpoint commands:

```bash
cd ~/projects/my-project
git init
git add .
git commit -m "Initialize project with AIPF"
```

## Update AIPF

```bash
git -C ~/tools/aipf pull --ff-only
~/tools/aipf/.venv/bin/python -m pip install --upgrade ~/tools/aipf
```

An update changes the installed CLI. It does not overwrite files in an
existing initialized project.

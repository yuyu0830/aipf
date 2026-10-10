#!/usr/bin/env bash
# Exercise publication against isolated repositories, never the real refs.
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel)"
python3.12 - "$repo_root/dev/scripts/update_release_branch.sh" "$repo_root/template" <<'PY'
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

script, template = map(Path, sys.argv[1:])
run = subprocess.run
options = dict(check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
root = template.parent
assert list(root.rglob('README.md')) == [template / 'README.md'], 'only product README is allowed'
assert not any((root / name).exists() for name in ('project', 'instructions', 'change', 'archive', 'inputs', 'knowledge', 'src'))
for area in ('dev', 'template'):
    for name in ('project/PROJECT_SPEC.md', 'project/PROJECT_STATUS.md', 'instructions/COMMON.md', 'instructions/GIT.md', 'knowledge/INDEX.md'):
        assert (root / area / name).is_file(), (area, name)
    assert run(['git', '-C', str(root), 'check-ignore', '-q', area + '/project/PROJECT_FLOW.md'], **options).returncode == 0
for name in ('change', 'archive'):
    assert sorted(p.name for p in (template / name).iterdir()) == ['.gitkeep']
assert '[작성]' in (template / 'project/PROJECT_SPEC.md').read_text()
assert 'markdown-redesign' not in (template / 'project/PROJECT_STATUS.md').read_text()
for document in [root / 'AGENTS.md', root / 'MEMORY_MAP.md', *list((root / 'dev').rglob('*.md')), *list(template.rglob('*.md'))]:
    if document.name == 'PROJECT_FLOW.md':
        continue
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', document.read_text()):
        path = target.split('#')[0]
        if path and '://' not in path and not path.startswith('mailto:'):
            assert (document.parent / path).exists(), (document, target)
print('PASS: development/product layout, only product README, links, ignored Flows, initial product state')

with tempfile.TemporaryDirectory(prefix='aipf-release-test-') as tmp:
    base = Path(tmp)
    repo = base / 'source'
    remote = base / 'origin.git'
    run(['git', 'init', '-b', 'main', str(repo)], **options)
    git = ['git', '-C', str(repo)]
    run(git + ['config', 'user.name', 'Release Test'], **options)
    run(git + ['config', 'user.email', 'release-test@example.invalid'], **options)
    shutil.copytree(template, repo / 'template', ignore=shutil.ignore_patterns('PROJECT_FLOW.md'))
    (repo / 'dev').mkdir()
    (repo / 'dev/private.txt').write_text('development data must not ship\n')
    (repo / 'AGENTS.md').write_text('development router\n')
    run(git + ['add', '.'], **options)
    run(git + ['commit', '-m', 'fixture: initial main'], **options)
    publish = ['bash', str(script)]
    call_options = dict(options, cwd=repo)

    before = {str(p): p.read_bytes() for p in (repo / '.git').rglob('*') if p.is_file()}
    run(publish + ['--check'], **call_options)
    after = {str(p): p.read_bytes() for p in (repo / '.git').rglob('*') if p.is_file()}
    assert before == after, '--check changed Git files'
    run(publish, **call_options)
    first = run(git + ['rev-parse', 'release'], **options).stdout.strip()
    assert run(git + ['rev-list', '--count', 'release'], **options).stdout.strip() == '1'
    source_tree = run(git + ['rev-parse', 'main:template'], **options).stdout
    assert source_tree == run(git + ['rev-parse', 'release^{tree}'], **options).stdout
    assert run(git + ['ls-tree', '-r', 'main:template'], **options).stdout == run(git + ['ls-tree', '-r', 'release'], **options).stdout
    files = run(git + ['ls-tree', '-r', '--name-only', 'release'], **options).stdout.splitlines()
    assert '.gitignore' in files and 'README.md' in files
    assert not any(p.startswith(('dev/', 'template/')) for p in files)
    run(publish, **call_options)
    assert first == run(git + ['rev-parse', 'release'], **options).stdout.strip()
    assert run(git + ['branch', '--show-current'], **options).stdout.strip() == 'main'
    assert not run(git + ['status', '--porcelain'], **options).stdout
    print('PASS: read-only check, first publication, exact tree/manifest, dotfiles, no-op, main unchanged')

    # Legacy release files disappear in a new commit whose parent is preserved.
    legacy = run(git + ['commit-tree', 'HEAD^{tree}', '-p', first, '-m', 'fixture: legacy CLI release'], **options).stdout.strip()
    run(git + ['update-ref', 'refs/heads/release', legacy, first], **options)
    run(publish, **call_options)
    second = run(git + ['rev-parse', 'release'], **options).stdout.strip()
    assert run(git + ['rev-parse', 'release^'], **options).stdout.strip() == legacy
    assert source_tree == run(git + ['rev-parse', 'release^{tree}'], **options).stdout

    for kind in ('untracked', 'unstaged', 'staged', 'branch', 'detached', 'missing-origin'):
        if kind == 'untracked':
            (repo / 'pending').write_text('pending')
        elif kind in ('unstaged', 'staged'):
            (repo / 'dev/private.txt').write_text('pending')
            if kind == 'staged':
                run(git + ['add', 'dev/private.txt'], **options)
        elif kind == 'branch':
            run(git + ['switch', '-c', 'change/test'], **options)
        elif kind == 'detached':
            run(git + ['switch', '--detach'], **options)
        result = run(publish + (['--push'] if kind == 'missing-origin' else []), cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert result.returncode != 0, kind
        assert second == run(git + ['rev-parse', 'release'], **options).stdout.strip(), kind
        if kind == 'untracked':
            (repo / 'pending').unlink()
        elif kind in ('unstaged', 'staged'):
            run(git + ['restore', '--source=HEAD', '--staged', '--worktree', 'dev/private.txt'], **options)
        elif kind in ('branch', 'detached'):
            run(git + ['switch', 'main'], **options)

    worktree = base / 'release-worktree'
    run(git + ['worktree', 'add', str(worktree), 'release'], **options)
    result = run(publish, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode != 0 and 'worktree' in result.stdout
    run(git + ['worktree', 'remove', str(worktree)], **options)

    # An invalid product snapshot must not replace a valid release.
    run(git + ['rm', 'template/README.md'], **options)
    run(git + ['commit', '-m', 'fixture: missing product README'], **options)
    result = run(publish, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode != 0 and 'missing' in result.stdout
    assert second == run(git + ['rev-parse', 'release'], **options).stdout.strip()
    run(git + ['restore', '--source=HEAD^', '--staged', '--worktree', 'template/README.md'], **options)
    run(git + ['commit', '-m', 'fixture: restore product README'], **options)
    for bad_path in ('dev/private.txt', 'template/private.txt', 'docs/README.md'):
        invalid = repo / 'template' / bad_path
        invalid.parent.mkdir(parents=True, exist_ok=True)
        invalid.write_text('must not ship\n')
        run(git + ['add', 'template'], **options)
        run(git + ['commit', '-m', 'fixture: invalid product path'], **options)
        result = run(publish, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert result.returncode != 0 and ('forbidden' in result.stdout or 'only its root README' in result.stdout), result.stdout
        assert second == run(git + ['rev-parse', 'release'], **options).stdout.strip()
        run(git + ['rm', 'template/' + bad_path], **options)
        run(git + ['commit', '-m', 'fixture: remove invalid product path'], **options)
    for bad_type in ('directory', 'symlink'):
        invalid = repo / 'template/README.md'
        invalid.unlink()
        if bad_type == 'directory':
            invalid.mkdir()
            (invalid / 'child').write_text('not a README file\n')
        else:
            invalid.symlink_to('AGENTS.md')
        run(git + ['add', '-A', 'template'], **options)
        run(git + ['commit', '-m', 'fixture: invalid required file type'], **options)
        result = run(publish, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert result.returncode != 0 and 'not a regular file' in result.stdout, result.stdout
        assert second == run(git + ['rev-parse', 'release'], **options).stdout.strip()
        run(git + ['rm', '-r', 'template/README.md'], **options)
        run(git + ['restore', '--source=HEAD^', '--staged', '--worktree', 'template/README.md'], **options)
        run(git + ['commit', '-m', 'fixture: restore regular README'], **options)
    print('PASS: reserved product paths, extra README, required directory/symlink rejected')
    print('PASS: legacy history preserved; dirty, wrong branch, detached, missing origin, worktree rejected')

    run(['git', 'init', '--bare', str(remote)], **options)
    run(git + ['remote', 'add', 'origin', str(remote)], **options)
    run(git + ['push', 'origin', 'main', 'release'], **options)
    (repo / 'template/product.txt').write_text('new product version\n')
    run(git + ['add', 'template/product.txt'], **options)
    run(git + ['commit', '-m', 'fixture: update template'], **options)
    result = run(publish + ['--push'], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode != 0 and 'differs' in result.stdout
    assert second == run(git + ['rev-parse', 'release'], **options).stdout.strip()
    run(git + ['push', 'origin', 'main'], **options)
    run(publish + ['--push'], **call_options)
    third = run(git + ['rev-parse', 'release'], **options).stdout.strip()
    assert run(git + ['rev-parse', 'release^'], **options).stdout.strip() == second
    assert third == run(['git', '--git-dir', str(remote), 'rev-parse', 'release'], **options).stdout.strip()
    assert run(git + ['rev-parse', 'main:template'], **options).stdout == run(git + ['rev-parse', 'release^{tree}'], **options).stdout
    before = {str(p): p.read_bytes() for p in (repo / '.git').rglob('*') if p.is_file()}
    run(publish + ['--check'], **call_options)
    after = {str(p): p.read_bytes() for p in (repo / '.git').rglob('*') if p.is_file()}
    assert before == after, 'remote --check changed local Git files'

    # A rejected push keeps a retryable local commit and does not duplicate it.
    hook = remote / 'hooks/pre-receive'
    hook.write_text('#!/bin/sh\nexit 1\n')
    hook.chmod(0o755)
    (repo / 'template/product.txt').write_text('retryable product version\n')
    run(git + ['add', 'template/product.txt'], **options)
    run(git + ['commit', '-m', 'fixture: pending publication'], **options)
    hook.unlink()
    run(git + ['push', 'origin', 'main'], **options)
    hook.write_text('#!/bin/sh\nexit 1\n')
    hook.chmod(0o755)
    result = run(publish + ['--push'], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode != 0 and 'push failed' in result.stdout
    pending = run(git + ['rev-parse', 'release'], **options).stdout.strip()
    assert pending != third
    assert third == run(['git', '--git-dir', str(remote), 'rev-parse', 'release'], **options).stdout.strip()
    hook.unlink()
    run(publish + ['--push'], **call_options)
    assert pending == run(git + ['rev-parse', 'release'], **options).stdout.strip()
    assert pending == run(['git', '--git-dir', str(remote), 'rev-parse', 'release'], **options).stdout.strip()

    # A remote race must be rejected by a normal non-fast-forward push.
    (repo / 'template/product.txt').write_text('racing product version\n')
    run(git + ['add', 'template/product.txt'], **options)
    run(git + ['commit', '-m', 'fixture: race'], **options)
    run(git + ['push', 'origin', 'main'], **options)
    competitor = run(git + ['commit-tree', 'HEAD^{tree}', '-p', pending, '-m', 'fixture: concurrent remote release'], **options).stdout.strip()
    run(git + ['push', 'origin', competitor + ':refs/test/competitor'], **options)
    hooks = base / 'source-hooks'
    hooks.mkdir()
    (hooks / 'pre-push').write_text('#!/bin/sh\ngit --git-dir=' + str(remote) + ' update-ref refs/heads/release ' + competitor + ' ' + pending + '\n')
    (hooks / 'pre-push').chmod(0o755)
    run(git + ['config', 'core.hooksPath', str(hooks)], **options)
    result = run(publish + ['--push'], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode != 0 and 'push failed' in result.stdout
    assert competitor == run(['git', '--git-dir', str(remote), 'rev-parse', 'release'], **options).stdout.strip()
    run(git + ['config', '--unset', 'core.hooksPath'], **options)
    local_before = run(git + ['rev-parse', 'release'], **options).stdout.strip()
    result = run(publish + ['--push'], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode != 0 and 'diverged' in result.stdout
    assert local_before == run(git + ['rev-parse', 'release'], **options).stdout.strip()
    print('PASS: unpublished main rejected, exact remote publication, read-only remote check, failed push retry, remote race/divergence rejected')

    # A competing local ref write between inspection and update must survive.
    run(git + ['remote', 'remove', 'origin'], **options)
    (repo / 'template/product.txt').write_text('local race product version\n')
    run(git + ['add', 'template/product.txt'], **options)
    run(git + ['commit', '-m', 'fixture: local ref race'], **options)
    rival = run(git + ['commit-tree', 'HEAD^{tree}', '-p', local_before, '-m', 'fixture: competing local ref'], **options).stdout.strip()
    shim = base / 'shim'
    shim.mkdir()
    real_git = shutil.which('git')
    (shim / 'git').write_text('#!/bin/sh\nif [ "$1" = update-ref ]; then\n  ' + real_git + ' -C ' + str(repo) + ' update-ref refs/heads/release ' + rival + ' ' + local_before + '\nfi\nexec ' + real_git + ' "$@"\n')
    (shim / 'git').chmod(0o755)
    env = dict(os.environ, PATH=str(shim) + os.pathsep + os.environ['PATH'])
    result = run(publish, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert result.returncode != 0 and 'cannot lock ref' in result.stdout, result.stdout
    assert rival == run(git + ['rev-parse', 'release'], **options).stdout.strip()
    print('PASS: missing product file and concurrent local ref overwrite rejected')

print('All release checks passed; temporary repositories removed.')
PY

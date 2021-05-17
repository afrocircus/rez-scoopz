#!/usr/bin/env python

import os
import sys
import time
import errno
import shutil
import zipfile
import argparse
import tempfile
import subprocess

from urllib.request import urlretrieve


def ask(msg):
    try:
        input()
    except NameError:
        # Python 2 support
        raw_input = input

    try:
        value = input(msg).lower().rstrip()  # account for /n and /r
        return value in ("", "y", "yes", "ok")
    except EOFError:
        return True  # On just hitting enter
    except KeyboardInterrupt:
        return False


def github_download(url, dst):
    yield "Downloading %s.." % os.path.basename(url)

    _, repo, _, branch = url.rsplit("/", 3)
    branch, _ = os.path.splitext(branch)

    tempdir = tempfile.mkdtemp()
    fname = os.path.join(tempdir, os.path.basename(url))
    urlretrieve(url, fname)

    yield "Extracting %s.." % os.path.basename(repo)

    try:
        with zipfile.ZipFile(fname) as f:
            f.extractall(tempdir)
    except (zipfile.BadZipfile, IOError):
        print("FAILED: '%s' likely not found" % url)
        exit(1)

    # Inner directory formatted as `repo-branch`
    branch_dir = os.path.join(tempdir, "%s-%s" % (repo, branch))

    try:
        os.makedirs(os.path.dirname(dst))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    shutil.copytree(branch_dir, dst)
    shutil.rmtree(tempdir)


def step(status, opts):
    # Download scoop
    stages = 4 + len(opts.bucket)
    width = 24
    stepsize = width // stages
    msg = "Installing scoopz [{:<%d}] ({}/{}) {}       \r" % width
    data = {"stage": 1}
    progress = "=" * stepsize * data["stage"]
    sys.stdout.write(msg.format(progress, data["stage"], stages, status))
    data["stage"] += 1


def build(source_path, build_path, install_path, opts, targets):

    def _build():
        # SCOOP_HOME hierarchy
        home_dir = os.path.join(build_path, "home")
        scoop_dir = os.path.join(home_dir, "apps", "scoop", "current")
        buckets_dir = os.path.join(home_dir, "buckets")
        cache_dir = os.path.join(home_dir, "cache")
        shims_dir = os.path.join(home_dir, "shims")

        version = opts.version.rsplit(".", 1)[0]  # Last digit is ours
        version = version.replace(".", "-")  # Rez to GitHub tag
        url = "https://github.com/lukesampson/scoop/archive/%s.zip" % version
        for status in github_download(url, scoop_dir):
            step(status, opts)

        for url in opts.bucket:
            _, repo, _, _ = url.rsplit("/", 3)
            bucket_dir = os.path.join(buckets_dir, repo.lower())
            for status in github_download(url, bucket_dir):
                step(status, opts)

        sys.stdout.write("\n")

        # Remaining empty dirs
        os.makedirs(cache_dir)
        os.makedirs(shims_dir)

        # python source
        src_py = os.path.join(source_path, "python")
        dest_py = os.path.join(build_path, "python")

        if not os.path.exists(dest_py):
            shutil.copytree(src_py, dest_py)

        src_bin = os.path.join(source_path, "bin")
        dest_bin = os.path.join(build_path, "bin")

        if not os.path.exists(dest_bin):
            shutil.copytree(src_bin, dest_bin)

        # Crippe automatic updates
        scoop_update_ps1 = os.path.join(scoop_dir, "libexec", "scoop-update.ps1")
        scoop_status_ps1 = os.path.join(scoop_dir, "libexec", "scoop-status.ps1")

        if not os.path.exists(scoop_update_ps1):
            print("WARNING: Couldn't disable Scoop's automatic updates, "
                  "the resulting package may try and update itself.")

        else:
            print("Disabling automatic updates")
            with open(scoop_update_ps1, "w") as f:
                f.write("exit 0\n")  # A winner every day!

            with open(scoop_status_ps1, "w") as f:
                f.write('success "Everything is ok!"\n')
                f.write('exit 0\n')

    def _install():
        if os.path.exists(install_path) and os.listdir(install_path):
            print("Previous install found %s" % install_path)

            if opts.overwrite or ask("Overwrite existing install? [Y/n] "):
                print("Cleaning existing install %s.." % install_path)
                assert subprocess.check_call(
                    'rmdir /S /Q "%s"' % install_path, shell=True
                ) == 0, "Failed"
            else:
                print("Aborted")
                exit(1)
        if os.path.exists(install_path):
            shutil.rmtree(install_path)

        shutil.copytree(build_path, install_path)

        print("Success!")
        time.sleep(0.2)

    _build()

    if "install" in (targets or []):
        _install()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--bucket", action="append", metavar=(
        "https://github.com/.../master.zip"), help=(
        "URLs to included buckets, compatible with this "
        "exact version of Scoop"
    ))

    opts = parser.parse_args()

    variants = os.environ["REZ_BUILD_VARIANT_REQUIRES"].split()
    if variants != ["platform-windows", "arch-AMD64"]:
        raise OSError("scoopz only supported on 64-bit Windows")

    build(
        source_path=os.environ['REZ_BUILD_SOURCE_PATH'],
        build_path=os.environ['REZ_BUILD_PATH'],
        install_path=os.environ['REZ_BUILD_INSTALL_PATH'],
        opts=opts,
        targets=sys.argv[1:]
    )


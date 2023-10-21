#!/usr/bin/env python

# This is a basic parsing script that will get the last commit
# of each repository in the RSEpedia given the current date.

__author__ = "Vanessa Sochat"
__copyright__ = "Copyright 2023, Vanessa Sochat"
__license__ = "MPL 2.0"

from rse.main import Encyclopedia
from rse.utils.command import Command
from rse.utils.file import write_json, read_json

from datetime import datetime
import tempfile
import shutil
import subprocess
import shlex
import argparse
import sys
import os

today = datetime.now()


def clone(url, dest):
    dest = os.path.join(dest, os.path.basename(url))
    cmd = Command("git clone --depth 1 %s %s" % (url, dest))
    cmd.execute()
    if cmd.returncode != 0:
        print("Issue cloning %s" % url)
        return
    return dest


def creation_date(repo, dest, filename):
    """
    Get the creation date for a file.
    """
    command = shlex.split(
        f"git -C {dest} log --diff-filter=A --follow --format=%ct -1 -- {filename}"
    )
    res = subprocess.check_output(command)
    ts = int(res.decode("utf-8").strip())
    timestr = str(datetime.fromtimestamp(ts))
    print(f"{repo.uid} was added to the database {timestr}")
    return timestr


def last_commit(repo, dest):
    """
    Get the date of last commit for a repository
    """
    command = shlex.split(f"git -C {dest} log -1 --format=%ct")
    res = subprocess.check_output(command)
    ts = int(res.decode("utf-8").strip())
    timestr = str(datetime.fromtimestamp(ts))
    print(f"{repo.uid} was last updated {timestr}")
    return timestr


def get_parser():
    parser = argparse.ArgumentParser(
        description="Research Software Encyclopedia Last Updated Analyzer",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--settings-file",
        dest="settings_file",
        help="custom path to settings file.",
    )

    parser.add_argument(
        "-o",
        "--outdir",
        help="Output directory for data.",
        default=os.path.join(os.getcwd(), "data"),
    )
    return parser


def main():
    p = get_parser()
    args, extra = p.parse_known_args()

    # Make sure output directory exists, organized by parsing date
    timestamp = "%s-%s-%s" % (today.year, today.month, today.day)
    outdir = os.path.abspath(os.path.join(args.outdir, timestamp))
    if not os.path.exists(outdir):
        print(f"Creating output directory {outdir}")
        os.makedirs(outdir)

    # Create a base temporary folder to work from
    tempdir = tempfile.mkdtemp()

    pedia = Encyclopedia(args.settings_file)
    repos = list(pedia.list())
    total = len(repos)

    # repository directory
    repo_dir = os.path.dirname(args.settings_file)

    # keep track of last updated commit
    meta = {}

    # We will save results as we go
    times_json = os.path.join(outdir, "last-commit-times.json")
    if os.path.exists(times_json):
        meta = read_json(times_json)

    # Parse the commit for when the file was added for each
    # This is our best estimate for a publication / release date
    # in the particular place it was parsed (give or take a week)
    print("🤓️ Looking for when each software repository was added to the database...")

    added = {}
    for i, reponame in enumerate(repos):
        print(f"{i} of {total}", end="\r")
        repo = pedia.get(reponame[0])

        # Get relative path of the filename to the repository
        filename = os.path.relpath(repo.filename, repo_dir)
        added[repo.url] = creation_date(repo, repo_dir, filename)

    for i, reponame in enumerate(repos):
        print(f"{i} of {total}", end="\r")

        # Prepare to clone the repository
        repo = pedia.get(reponame[0])
        if not repo.url or repo.url in meta:
            print(f"Skipping {repo.url}")
            continue

        dest = None
        try:
            # Try clone (and cut out early if not successful)
            dest = clone(repo.url, tempdir)
            if not dest:
                continue
            meta[repo.url] = last_commit(repo, dest)

        except:
            print(f"Issue with {repo.url}, skipping")

        try:
            if dest and os.path.exists(dest):
                shutil.rmtree(dest)
        except:
            write_json(meta, times_json)
            sys.exit(
                "Likely too many files, check with ulimit -n and set with ulimit -n 4096"
            )

        # Save as we go
        write_json(meta, times_json)

    # One final save
    write_json(meta, times_json)

    # Write the combined results
    results_json = os.path.join(outdir, "results.json")
    results = {}
    for url, timestamp in meta.items():
        results[url] = {"last_commit": timestamp, "added_rsepedia": added[url]}
    write_json(results, results_json)


if __name__ == "__main__":
    main()

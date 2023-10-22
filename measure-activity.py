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
import requests
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


def look_for_doi(repo):
    """
    A lot of records have a DOI, and the publication date is a more
    accurate assessment than when it was added to the rsepedia.
    """
    url = "https://zenodo.org/api/records"
    doi = repo.data.get("doi") or repo.data.get("data", {}).get("doi")
    if not doi:
        return doi, None
    if isinstance(doi, list):
        doi = doi[0]

    # Rate limit is 5000/hour, we should be ok
    if "zenodo" not in doi:
        return doi, None

    record_id = os.path.basename(doi).split(".")[-1]
    zenodo_url = f"{url}/{record_id}"
    r = requests.get(zenodo_url)
    record = r.json()

    # We can't get an API response
    if "metadata" not in record:
        return doi, None

    published = record["metadata"]["publication_date"]
    print(f"Found actual publication date {published} for {doi}")
    return doi, published


def derive_creation_timestamps(pedia, outdir, added_json, settings_file):
    """
    Parse the commit for when the file was added for each
    This is our best estimate for a publication / release date
    in the particular place it was parsed (give or take a week)
    """
    print("🤓️ Looking for when each software repository was added to the database...")
    print("If a zenodo DOI is provided, we can use that instead.")

    repos = list(pedia.list())
    total = len(repos)

    # repository directory
    repo_dir = os.path.dirname(settings_file)

    added = {}
    if os.path.exists(added_json):
        added = read_json(added_json)

    for i, reponame in enumerate(repos):
        print(f"{i} of {total}", end="\r")
        repo = pedia.get(reponame[0])
        if repo.url in added:
            continue
        doi, published = look_for_doi(repo)

        # Get relative path of the filename to the repository
        filename = os.path.relpath(repo.filename, repo_dir)
        created_at = creation_date(repo, repo_dir, filename)
        added[repo.url] = {"created_at": created_at, "doi": doi, "published": published}
    return added


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

    # keep track of last updated commit
    meta = {}

    # We will save results as we go, and use cached results for the day if exist
    times_json = os.path.join(outdir, "last-commit-times.json")

    if os.path.exists(times_json):
        meta = read_json(times_json)

    added_json = os.path.join(outdir, "rsepedia-times.json")

    # This should be refactored into a nice class, this function is kind of janky
    added = derive_creation_timestamps(pedia, outdir, added_json, args.settings_file)
    write_json(added, added_json)

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

    # We have dates for when added to the rsepedia and published
    for url, timestamp in meta.items():
        # The more accurate is likely zenodo
        published = added[url]["created_at"]
        zenodo_published = added[url]["published"]
        if zenodo_published:
            published = zenodo_published
        results[url] = {
            "last_commit": timestamp,
            "added_rsepedia": added[url]["created_at"],
            "zenodo_published": added[url]["published"],
            "published": published,
            "doi": added[url]["doi"],
        }

    write_json(results, results_json)


if __name__ == "__main__":
    main()

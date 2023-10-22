import argparse
import pandas
from rse.utils.file import read_json, write_json
import matplotlib.pyplot as plt
import seaborn as sns
import os

plt.style.use("bmh")
here = os.path.dirname(os.path.abspath(__file__))


def get_parser():
    parser = argparse.ArgumentParser(
        description="Plot RSEPedia Activity",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--results",
        help="json file with results",
    )
    parser.add_argument(
        "--out",
        help="directory to save parsed results",
        default=os.path.join(here, "img"),
    )
    return parser


def main():
    """
    Run the main plotting operation!
    """
    parser = get_parser()
    args, _ = parser.parse_known_args()

    # Output images and data
    outdir = os.path.abspath(args.out)
    infile = os.path.abspath(args.results)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    if not infile or not os.path.exists(infile):
        raise ValueError("Please provide an existing results.json with --results")

    # This does the actual parsing of data into a formatted variant
    # Has keys results, iters, and columns
    results = read_json(infile)

    # Convert to dataframe for easy viewing later
    df = prepare_data_frame(results)
    results_dir = os.path.dirname(infile)
    df.to_csv(os.path.join(results_dir, "results.csv"))

    # And plot!
    # plot_results(df, outdir)

    # Derive high valued repositories, and also save
    derive_high_valued(df, outdir, results_dir)


def derive_high_valued(df, outdir, results_dir):
    """
    Derive highly valued software, as indicated by updates over time.
    """
    # Save high value repos after 24 months
    high_valued = {}

    # And how many are updated at each period
    updated_at_period = []

    # Figure out "highly valued" projects, or those with commits at least six months and one year after publication
    months = range(0, 41)
    for month in months:
        df[f"{month}_months_post_add"] = df.published_date + pandas.DateOffset(
            months=month
        )
        df[f"{month}_months_high_value"] = (
            df.last_commit_date > df[f"{month}_months_post_add"]
        )
        updated_repos = df[df[f"{month}_months_high_value"] == True].repo.tolist()
        update_count = len(updated_repos)
        updated_at_period.append(update_count)
        print(f"There are {update_count} repos at {month} months")
        if month >= 24:
            high_valued[month] = updated_repos

    plt.figure(figsize=(10, 8))
    plt.plot(list(months), updated_at_period)
    plt.title("Number of updated repositories after likely publication")
    plt.xlabel("Months post addition", fontsize=16)
    plt.ylabel("Number of updated repositories", fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "updated-repos-over-time.png"))
    plt.clf()
    plt.close()
    write_json(high_valued, os.path.join(results_dir, "highest-value.json"))


def prepare_data_frame(data):
    """
    Given results data, parse into data frame
    """
    # Assemble times into dataframe.
    df = pandas.DataFrame(
        columns=[
            "repo",
            "last_commit_date",
            "added_database_date",
            "added_zenodo_date",
            "published_date",
            "doi",
        ]
    )
    idx = 0
    for url, meta in data.items():
        last_commit = meta["last_commit"].split(" ")[0].strip()
        added = meta["added_rsepedia"].split(" ")[0].strip()
        zenodo = None
        if meta["zenodo_published"] is not None:
            zenodo = meta["zenodo_published"].split(" ")[0].strip()

        # This is zenodo and added squashed, we only use rsepedia if no zenodo
        published = meta["published"].split(" ")[0].strip()
        df.loc[idx, :] = [url, last_commit, added, zenodo, published, meta["doi"]]
        idx += 1

    # Round to nearest week for added_database
    df["added_database_date"] = pandas.to_datetime(df.added_database_date)
    df["published_date"] = pandas.to_datetime(df.published_date)

    # Turn these into pandas dates
    df["last_commit_date"] = (
        pandas.to_datetime(df.last_commit_date).dt.to_period("D").dt.start_time
    )
    df["added_zenodo_date"] = (
        pandas.to_datetime(df.added_zenodo_date).dt.to_period("D").dt.start_time
    )
    df["added_database_week"] = (
        df["added_database_date"].dt.to_period("W").dt.start_time
    )
    return df


def plot_results(df, outdir):
    """
    Make plots for each result item.
    """
    # This includes our best effort for the published data (zenodo and rsepedia added)
    plt.figure(figsize=(18, 10))
    ax = sns.scatterplot(data=df, x="added_database_week", y="last_commit_date")
    outfile = os.path.join(outdir, "last-commit-function-of-rsepedia-added.png")
    make_plot(
        ax,
        title="Last Commit vs. Database Addition",
        outfile=outfile,
        ylabel="Last commit date (proxy for activity)",
        xlabel="Date added to database (proxy for publication)",
    )

    # This only included zenodo, for those skeptical of the RSEpedia
    plt.figure(figsize=(18, 10))

    # There are 864 records here, much smaller
    subset = df[df.added_zenodo_date.isnull() == False]
    ax = sns.scatterplot(data=subset, x="added_zenodo_date", y="last_commit_date")
    outfile = os.path.join(outdir, "last-commit-function-of-added-zenodo.png")
    make_plot(
        ax,
        title="Last Commit vs. Zenodo Publication",
        outfile=outfile,
        ylabel="Last commit date (proxy for activity)",
        xlabel="Date published Zenodo",
    )


def make_plot(ax, title, outfile, xlabel=None, ylabel=None):
    """
    Generic plot making function for some x and y
    """
    plt.title(title, fontsize=28)

    # For bandwith, higher is better
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=20)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=20)
    # ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
    # ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    plt.tight_layout()
    plt.savefig(outfile)
    plt.clf()
    plt.close()


if __name__ == "__main__":
    main()

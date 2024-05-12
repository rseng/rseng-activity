# Research Software Activity

I have a strong opinion about research software, and that is that it is a living and changing thing. If you stumble on a repository that claims to be research software that hasn't had activity in years? I would suspect it was a one-off set of scripts created for one person and then forgotten. Yes, there are larger reasons behind that (e.g., problems with the funding and incentive model) but for now we can assume that software development operates on this imperfect system, and that (what I deem "true" research software, again entirely my opinion) has the quality that it continues to be valued and this is reflected in continued requests for change (features, bug fixes, updates, etc.) by the user base. This gives me a solid (and simple) foundation to do a small study, primarily for my own interest.

- In the Research Software Encyclopedia (a sampling of this universe) when were projects last updated (by way of commit to a main branch?)
- Given groups of update frequencies, where do we see these being published?

I have a hunch that particular jounals select for different tiers of research software (e.g. true projects that will be valued over time and thus changed vs. one-off ones) but I will keep this to myself for now.

## Usage

Because the research software encyclopedia is a database, this is fairly easy to implement this analysis. And we can be lazy and do one off git clones and cleanups to get the last commit of the latest branch. First, download the database:

```bash
git clone https://github.com/rseng/software /tmp/software
```

It's important you get the full clone so we can see when the software was added to the database, which
is indicative of when it likely was added to the respective database (or within a week). Then install dependencies:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

And run the script, targeting the database.

```bash
python measure-activity.py --settings-file /tmp/software/rse.ini -o ./data
```

This will generate timestmaps and results that include the last commit and the date when the software
was added to the RSEpedia, which (for non-early entries) we can use as a proxy for when it was "done" or
"published."  Note that when a repository is deleted or not found, you need to press enter to advance through
the request through authentication. If you hit a file limit it will give a helpful message to run, and you
can run the command again - it will pick up where you left off. Just be careful if you go after midnight and
the date changes.

## Analysis

The script can be run. Note that the original run from 2023 I put `--out` into img, and after that updated to put alongside the dated folder.

```bash
python plot-activity.py --results ./data/2024-5-12/results.json --out ./data/2024-5-12/img
```

and I want to answer the following questions:

- How does time added to the database (a proxy for the software being finished or published) relate to activity, as measured by the last commit?
- What are the "highly valued" projects (indicated by last commit activity)


A question I probably don't have time to answer:

- How does this distribution compare to an average GitHub project (e.g., perhaps by language)?

I'll write this up more fully in a blog post. I think I've uncovered some expected (but still interesting) patterns.

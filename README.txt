CODEFORCES WEEKLY TRACKER

Same three separate commands as before - each does one job:

CREATE WEEK:
    python newweek.py

ADD PROBLEMS:
    python add.py week1

It now only asks for:
    URL

The problem name and rating are fetched automatically from the
Codeforces API. You only get asked to type a name/rating yourself if
the auto-lookup fails (this basically only happens for gym problems,
or if you're offline).

Type done when finished.

WRITE LOGIC / SOLVE:
    python logic.py week1

Choose by:
    number
    problem name
    URL
    or the short tag shown next to each problem (e.g. 1985F)

Write logic, then type:
    END

Then answer:
    y = solved + checkbox saved
    n = review

OTHER:
- Closing the terminal does not lose already-added problems.
- add.py prevents the same problem being added twice, even if you
  paste the link in a different form (contest/... vs problemset/...).
- cf_cache.json is created automatically to speed up repeated lookups
  in add.py - safe to delete anytime, it just rebuilds itself.
- index.html lists all weeks.
- style.css controls the design. Problems marked for revision (n) now
  get a distinct amber highlight so they stand out from unsolved ones.
- No database/server/login is required.

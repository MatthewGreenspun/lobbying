# Deploy: NY Lobbying Filings on GitHub Pages (free, auto-updating)

You get a public web page like `https://YOURNAME.github.io/ny-lobbying/` that
shows the newest NY lobbying filings and refreshes itself about every 15 minutes
— no server, no database, nothing to maintain. Anyone you send the link to just
opens it; they need no account.

Everything below can be done **in the browser, no terminal**. ~5 minutes, once.

## What's in this folder

```
public/index.html      the web page (static)
public/latest.json     the data (pre-filled now; the workflow overwrites it)
scripts/generate.py    fetches the newest filings and writes latest.json
scripts/core.py        the fetch/parse logic
requirements.txt       one dependency (requests)
.github/workflows/refresh.yml   runs the fetch every 15 min and publishes
```

## Steps

1. **Create a GitHub account** if you don't have one — <https://github.com/signup>.
   Email + password, no credit card.

2. **Create a repository.** Click **+ → New repository**. Name it e.g.
   `ny-lobbying`. Choose **Public**. Click **Create repository**.

3. **Upload these files.** On the new repo page, click
   **"uploading an existing file"** (or **Add file → Upload files**). Drag the
   **contents of this folder** in (the `public`, `scripts`, `.github` folders and
   `requirements.txt`), then **Commit changes**.
   - Tip: if drag-and-drop skips the `.github` folder, upload the file
     `.github/workflows/refresh.yml` on its own — keep that exact path.

4. **Turn on Pages.** Repo **Settings → Pages**. Under **Build and deployment →
   Source**, choose **GitHub Actions**. (No branch to pick; the workflow
   publishes for you.)

5. **Run it once.** Go to the **Actions** tab. If prompted, click **"I understand
   my workflows, enable them."** Select **Refresh filings** → **Run workflow → Run
   workflow**. Wait ~1–2 minutes for the green check.

6. **Open your site.** Back in **Settings → Pages**, your URL is shown at the top
   (`https://YOURNAME.github.io/ny-lobbying/`). That's the link to share.

Done. From now on it updates on its own every ~15 minutes.

## Good to know

- **It's free because the repo is public** — GitHub Actions minutes are unlimited
  for public repos, and Pages hosting is free. (Public is fine: this is public
  data and there are no secrets in the code.)
- **Timing:** GitHub runs scheduled jobs about every 15 min but can delay them a
  few minutes when busy. Not to-the-second, which is fine here.
- **One rare caveat:** GitHub pauses *scheduled* workflows after **60 days with no
  activity in the repo**. If the site ever stops updating, open the **Actions**
  tab and click **Run workflow** once — it resumes. (Any commit also resets it.)
- **To change how many filings show:** edit the number in
  `.github/workflows/refresh.yml` (`python scripts/generate.py 50`).

## Faster path if you use the command line

With the GitHub CLI (`gh`) installed:

```bash
gh repo create ny-lobbying --public --source=. --push   # from inside this folder
gh api -X POST repos/:owner/ny-lobbying/pages -f build_type=workflow  # enable Pages
gh workflow run "Refresh filings"
```

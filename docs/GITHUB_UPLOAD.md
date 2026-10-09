# Upload this project to GitHub (macOS)

## 1. Run it locally first

```bash
cd /path/to/IT-Helpdesk-Asset-Support
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Visit `http://127.0.0.1:5000`, create a ticket, assign a technician, record a resolution and inspect Reports. In a second Terminal tab, the route/database tests can be run with:

```bash
python -m unittest discover -s tests -v
```

## 2. Create an empty GitHub repository

1. Sign in to GitHub and choose **New repository**.
2. Suggested repository name: `IT-Helpdesk-Asset-Support-Management`.
3. Set visibility to **Public** if the faculty requires public access.
4. Leave **Add a README**, `.gitignore` and license unchecked because those files are already in this project.
5. Create the repository and copy its HTTPS URL.

## 3. Commit and push the local project

Run these commands from the project folder. Replace `YOUR_USERNAME` with your GitHub username and ensure the remote URL matches the repository you created.

```bash
git init -b main
git add .
git status
git commit -m "Build IT helpdesk and asset support prototype"
git remote add origin https://github.com/YOUR_USERNAME/IT-Helpdesk-Asset-Support-Management.git
git push -u origin main
```

`git status` is an important check before committing: `.venv`, local `.db` files, `.env` files and secrets should not be included. The current `.gitignore` excludes local virtual environments and the generated SQLite database.

## 4. Verify the public repository

Open the repository in a private/incognito browser window (signed out) and check that `README.md`, `app.py`, `sql/`, `docs/`, `templates/`, `static/` and `tests/` are visible. Later, add the three phase slide decks, final report and the document containing the public Google Drive video URL before final submission.

## If Git asks for credentials

Use GitHub's browser-based authentication or a personal access token through a supported credential manager. Never put a token in the remote URL, commit it to source code, or share it in chat.

# Trackroom: Internal Tracker

[![CI](https://github.com/agustusgeorge-ship-it/Internal-Tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/agustusgeorge-ship-it/Internal-Tracker/actions/workflows/ci.yml)

Trackroom is a full-stack Django web app that tracks a company's IT equipment through its whole life. New starters create an account and choose the laptop, monitor, phone and accessories they need. A manager approves or rejects each request. Every item's condition and holder is recorded, and when someone leaves, the manager logs the handback and the item goes back into stock, or for repair if it came back damaged.

It was built for the Code Institute Full Stack bootcamp capstone, to show full CRUD (Create, Read, Update, Delete) behind a real login system with two user roles.

**Live site: [https://internal-tracker-agustus-7f7416195a35.herokuapp.com/](https://internal-tracker-agustus-7f7416195a35.herokuapp.com/)**

![Trackroom manager dashboard](docs/images/12-manager-dashboard.png)

## UX design

### Purpose and audience

Companies lose track of laptops. New starters arrive with no equipment ready, and leavers walk out with kit nobody recorded. Trackroom gives two groups one shared place to work:

| Who | What they need |
|---|---|
| **Employees** (new starters, current staff, leavers) | Choose the right equipment before day one, see whether a manager has approved it, and know what they will need to hand back. |
| **Managers** (IT or office managers) | One stock list with condition and status, a queue of requests to approve or reject, and a record of who holds what. |

### User stories

There are 19 user stories, prioritised with MoSCoW: 12 Must, 4 Should, 3 Could, plus a "Won't have this version" list. Each one has acceptance criteria and is a GitHub issue on the project board. The full text is in [docs/USER_STORIES.md](docs/USER_STORIES.md).

| ID | As a... I can... | Priority |
|---|---|---|
| EST-01 | As a new employee, I can create an account and log in and out | Must |
| EST-02 | As a manager, I want employees to only see and change their own requests | Must |
| EST-03 | As a manager, I can add a piece of equipment to stock | Must |
| EST-04 | As a manager, I can update an item and mark its condition good, fair or bad | Must |
| EST-05 | As a manager, I can remove an item that was lost or scrapped | Must |
| EST-06 | As a new employee, I can browse the equipment available to me | Must |
| EST-07 | As a new employee, I can request one or more pieces of equipment (Create) | Must |
| EST-08 | As an employee, I can see my requests and their status (Read) | Must |
| EST-09 | As an employee, I can change my choice while it is pending (Update) | Must |
| EST-10 | As an employee, I can cancel a pending request (Delete) | Must |
| EST-11 | As a manager, I can approve or reject an employee's choice | Must |
| EST-12 | As a manager, I can record a leaver handing equipment back, and its condition | Must |
| EST-13 | As a manager, I see a dashboard of what needs my attention | Should |
| EST-14 | As an employee, I can see the equipment assigned to me | Should |
| EST-15 | As a user, I get a clear message after every action | Should |
| EST-16 | As a user on any device, I can use every page comfortably | Should |
| EST-17 | As a manager, I can search and filter the stock list | Could |
| EST-18 | As an employee, I can see photos of each laptop | Could (not built: type icons used instead) |
| EST-19 | As an employee, I get an email when my request is decided | Could (not built) |

### Wireframes

Low-fidelity wireframes were drawn in before building. The finished pages follow them closely; the screenshots under [Features](#features) show the result.

| Employee: catalogue (desktop) | Manager: review a request (desktop) |
|---|---|
| ![Employee catalogue wireframe](docs/wireframes/01-employee-catalogue-desktop.png) | ![Manager review wireframe](docs/wireframes/02-manager-review-desktop.png) |

On a phone (375px), the sidebar becomes a top bar, cards stack in one column, and table rows turn into labelled cards.

![Phone wireframe: my requests](docs/wireframes/03-phone-my-requests.png)

### Design

- **Layout:** a dark navy sidebar for logged-in users (kept from the project's first "Trackroom" design), with a light workspace. Below 960px the sidebar becomes a top bar. Below 640px, tables turn into one labelled card per row, so nothing scrolls sideways.
- **Colour:** blue for main actions, green for approve, red for reject and delete, and purple to show the current page. Every text and background pair meets WCAG AA contrast (checked with axe, see [TESTING.md](TESTING.md)).
- **Status badges** always carry words ("Pending", "Bad (needs repair)"), so meaning never depends on colour alone.
- **Icons:** each equipment type has a simple line icon (laptop, monitor, phone, keyboard, router) drawn in inline SVG, so no image files or photo uploads are needed.
- **Type:** the system font stack (Segoe UI, system-ui, Arial) at a 16px base, for speed and readability.

## Database design

Three custom models sit alongside Django's built-in `User`. Being a manager is Django's `is_staff` flag, so no extra role table is needed.

```mermaid
erDiagram
    USER ||--o{ EQUIPMENT_REQUEST : "makes"
    USER ||--o{ EQUIPMENT : "holds (assigned_to)"
    USER ||--o{ HANDBACK : "returns"
    EQUIPMENT ||--o{ EQUIPMENT_REQUEST : "is requested in"
    EQUIPMENT ||--o{ HANDBACK : "is returned in"

    USER {
        int id PK
        string username
        string email
        bool is_staff "True = manager"
    }
    EQUIPMENT {
        int id PK
        string name
        string serial_number UK
        string equipment_type "laptop, monitor, phone, peripheral, infrastructure"
        string specification
        string condition "good, fair, bad"
        string status "in_stock, reserved, assigned, in_repair, retired"
        string location
        text notes
        int assigned_to FK "nullable"
    }
    EQUIPMENT_REQUEST {
        int id PK
        int employee FK
        int equipment FK
        string job_title
        date start_date
        text note
        string status "pending, approved, rejected"
        text manager_note
        int reviewed_by FK "nullable"
        datetime reviewed_at
    }
    HANDBACK {
        int id PK
        int equipment FK
        int employee FK
        date returned_on
        string condition_on_return
        text notes
        int checked_by FK
    }
```

**Rules the database enforces itself**

- `serial_number` is unique.
- A partial unique constraint (`one_pending_request_per_item`) stops two pending requests for the same item, even if two people press "Request" at the same moment.
- `on_delete=PROTECT` stops deleting an item that has requests or handbacks, or a user who still holds equipment, so history cannot be lost by accident.

**How an item moves through its life.** All of this lives in `equipment/models.py`, so the views and the admin follow the same rules.

```mermaid
stateDiagram-v2
    [*] --> InStock: manager adds item
    InStock --> Reserved: employee requests it
    Reserved --> InStock: request rejected or cancelled
    Reserved --> Assigned: manager approves
    Assigned --> InStock: handed back good or fair
    Assigned --> InRepair: handed back bad
    InRepair --> InStock: manager marks it fixed
    InStock --> Retired: manager retires it
```

## Features

### Accounts and roles

- **Register:** username, first and last name, work email (must be unique) and password, checked by Django's password rules. New users are logged in straight away and taken to the catalogue. The public form can only ever create an employee.
- **Log in and log out:** every login shows "You are logged in as ..." and every logout shows "You have been logged out." Logout is a POST form with a CSRF token.
- **Always clear who you are:** the sidebar shows "Logged in as **name**" and the role (Employee or Manager).

| Register | Wrong password |
|---|---|
| ![Registration form](docs/images/02-register.png) | ![Login error](docs/images/11-login-error.png) |

### Employees: catalogue and full front-end CRUD on requests

- **Catalogue (Read):** only items that are in stock and in good or fair condition appear. Filter by type with the tabs, or search by name or spec. Laptops are listed first.
- **Request equipment (Create):** pick an item, add your job title, start date and a note for the manager. The item is reserved at once so nobody else can take it. One pending request per type is allowed (one laptop, one monitor and so on), and the start date cannot be in the past.
- **My requests (Read):** status badges, the date needed, and the manager's note, including the reason if a request was rejected.
- **Change a request (Update):** swap to a different item, or change the date or note, while the request is still pending. Swapping frees the old item and reserves the new one.
- **Cancel a request (Delete):** a confirmation page first; the item goes back into stock.
- **My equipment:** everything assigned to you, with serial numbers, so leavers know what to hand back.

| Catalogue | Request form |
|---|---|
| ![Catalogue](docs/images/03-catalogue.png) | ![Request form](docs/images/04-request-form.png) |

| My requests, with edit and cancel | Validation: one laptop at a time |
|---|---|
| ![My requests](docs/images/06-my-requests.png) | ![Validation error](docs/images/05-request-validation.png) |

| Cancel confirmation | Employee opening a manager page |
|---|---|
| ![Cancel confirmation](docs/images/07-cancel-confirm.png) | ![403 page](docs/images/08-403.png) |

### Managers: approvals, stock CRUD and handbacks

- **Dashboard:** pending requests, items in stock, items assigned and items needing attention, plus new starters with requests due in the next 14 days. Every count links to the matching filtered list.
- **Request queue:** pending requests, soonest start date first, with a "Decided" tab for history. The sidebar shows a badge with the number pending.
- **Review a request:** the employee's details, job title, start date, note and what they already hold. **Approve** (with an optional note) assigns the item to them. **Reject** needs a reason, which the employee sees.
- **Stock (full CRUD):** add, view, edit and delete equipment. Search by name, serial number or location, and filter by type, status, condition or holder. Serial numbers are stored in capitals and must be unique. The status cannot be changed by hand while an item is reserved or assigned. Items with history cannot be deleted; the page explains how to retire them instead.
- **Item history:** every request and handback for an item, with who decided and when.
- **Handback:** record the return date, condition and notes. Good or fair items go back in stock; bad items go to repair.
- **People:** every employee with their pending requests and the items they hold, which is where a manager checks a leaver's equipment.
- **Django admin** (`/admin/`): a back office for all records, with filters and a bulk "Approve selected" action. Workflow fields are read-only there, so the admin cannot put an item into an impossible state.

| Request queue | Review: approve or reject |
|---|---|
| ![Request queue](docs/images/13-request-queue.png) | ![Review request](docs/images/14-request-review.png) |

| Item detail and history | Record a handback |
|---|---|
| ![Item detail](docs/images/16-item-detail.png) | ![Handback form](docs/images/17-handback.png) |

| Add equipment, with validation | People |
|---|---|
| ![Add equipment errors](docs/images/18-add-equipment-errors.png) | ![People page](docs/images/19-people.png) |

### Responsive design

| Phone: catalogue | Phone: my requests | Phone: stock list | Tablet: dashboard |
|---|---|---|---|
| ![Mobile catalogue](docs/images/09-mobile-catalogue.png) | ![Mobile requests](docs/images/10-mobile-requests.png) | ![Mobile stock](docs/images/20-mobile-stock.png) | ![Tablet dashboard](docs/images/21-tablet-dashboard.png) |

### Accessibility and quality

- Skip link, visible focus outline, labelled form fields, `aria-current` on the active page, and screen-reader text on repeated buttons (for example "Edit request for MacBook Air").
- Success messages use `role="status"` and errors use `role="alert"`, so screen readers announce them.
- Custom 403, 404 and 500 pages.
- No JavaScript is needed anywhere: every feature is a normal link or form.

### Future features

- Email the employee when a request is decided (EST-19).
- Photos of each item (EST-18).
- Bundles: request a "developer starter kit" in one go.
- Reminders to managers about leavers' handback dates.

## Agile methodology

The project was planned and tracked on a public GitHub Projects board: **[add the project board link here](https://github.com/users/agustusgeorge-ship-it/projects/)**.

- Each user story is a GitHub issue created from the repository's **User Story Template** (`.github/ISSUE_TEMPLATE/user-story-template.md`), with acceptance criteria and tasks.
- Each issue has a MoSCoW label: `must-have`, `should-have` or `could-have`.
- The board has the columns **To do**, **In progress** and **Done**.
- The Must stories were built first, in this order: accounts and roles, stock, requests, approvals, then handbacks. Should and Could stories followed. See the build order in [docs/USER_STORIES.md](docs/USER_STORIES.md).

## Testing

The full testing write-up is in **[TESTING.md](TESTING.md)**. In summary:

- **80 automated Django tests**, all passing, covering **97%** of the code. They include two-user tests proving one employee cannot see, edit or cancel another's request, and that employees get a 403 on every manager page.
- **flake8** (PEP 8): no problems.
- **W3C HTML validator:** 23 pages, 0 errors, 0 warnings.
- **W3C CSS validator:** 0 errors.
- **axe accessibility engine (WCAG 2.1 AA):** 24 page checks, 0 violations.
- **Browser test:** 45 checks through the full journey in Chrome, including no sideways scrolling at 320px, 375px and 768px.
- **GitHub Actions CI** runs flake8, a missing-migrations check and every test on each push.

## Security

- **No secrets in the code.** `SECRET_KEY`, database details and `DEBUG` come from environment variables (Heroku config vars) or, locally, from `config/env.py`, which `.gitignore` excludes.
- **DEBUG is off unless switched on.** If `DEBUG` is missing, it is treated as off. In production the site refuses to start without a real `SECRET_KEY` and `ALLOWED_HOSTS`.
- **HTTPS in production:** HTTPS redirect, secure cookies and HSTS (one year), plus `X-Frame-Options: DENY` and a same-origin referrer policy.
- **Access is checked on the server, not just hidden in the page:** every private page needs a login, employee lookups are filtered to their own records (anything else returns 404), and manager pages return 403 to employees.
- **Every form is protected:** CSRF tokens on all forms, deletes and decisions use POST only, and the employee and manager are set from the logged-in user, never from the form.

## Deployment

### Run it on your own computer

1. Clone the repository and open it in VS Code:
   ```bash
   git clone https://github.com/agustusgeorge-ship-it/Internal-Tracker.git
   cd Internal-Tracker
   ```
2. Create and activate a virtual environment, then install the packages:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create `config/env.py` (it is git-ignored, so it never reaches GitHub):

   | Variable | Example value | What it is |
   |---|---|---|
   | `SECRET_KEY` | a long random string | Make one with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DEBUG` | `True` | Only ever `True` on your own computer |
   | `ALLOWED_HOSTS` | `"127.0.0.1,localhost"` | Addresses the site answers on |
   | `DATABASE_ENGINE` | `"sqlite"` | Or `"postgresql"` plus `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` |

4. Build the database, load the demo equipment and create a manager account:
   ```bash
   python manage.py migrate
   python manage.py seed_equipment
   python manage.py createsuperuser
   ```
5. Run it with `python manage.py runserver` and open http://127.0.0.1:8000/. Log in with the superuser to see the manager pages, or register a new account to see the employee side.
6. Run the tests with `python manage.py test`.

### Deploy to Heroku

The live site runs on Heroku with a Heroku Postgres database. This is how it was deployed, using the Heroku CLI:

1. Log in: `heroku login`
2. Create the app in the Europe region: `heroku create internal-tracker-agustus --region eu`
3. Add the database (this sets `DATABASE_URL` automatically): `heroku addons:create heroku-postgresql:essential-0`
4. Set the config vars with `heroku config:set`. The values are never stored in the repository:

   | Key | Value |
   |---|---|
   | `SECRET_KEY` | a newly generated random string |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | the app's exact hostname, without `https://` |
   | `CSRF_TRUSTED_ORIGINS` | `https://` plus the app's exact hostname |

5. Deploy: `git push heroku main`. Heroku installs `requirements.txt`, runs `collectstatic`, then the `Procfile` release step runs `migrate` before gunicorn starts.
6. Load the demo equipment and create a manager: `heroku run python manage.py seed_equipment`, then `heroku run python manage.py createsuperuser`.
7. Open the site with `heroku open`.

A problem met during deployment: the first page load returned a 400 error because `ALLOWED_HOSTS` did not match the app's full hostname, which includes a random suffix. Setting the exact hostname fixed it.

### Forking or cloning

Fork the repository on GitHub (top-right **Fork** button) or clone it as above, then follow "Run it on your own computer".

## Credits

### Code

- [Django documentation](https://docs.djangoproject.com/en/5.2/): class-based views, `LoginRequiredMixin`, `UserPassesTestMixin`, `UniqueConstraint` with a condition, `select_for_update`, the messages framework and the auth signals.
- [WhiteNoise documentation](https://whitenoise.readthedocs.io/): serving static files on Heroku.
- [dj-database-url](https://github.com/jazzband/dj-database-url): reading Heroku's `DATABASE_URL`.
- Code Institute course material: Django deployment to Heroku.
- The "table rows become cards on mobile" pattern is a widely used CSS technique (`display: block` rows with `data-label` captions).

### Tools

- [W3C HTML validator](https://validator.w3.org/nu/), [W3C CSS validator](https://jigsaw.w3.org/css-validator/), [axe-core](https://github.com/dequelabs/axe-core), [Playwright](https://playwright.dev/), [flake8](https://flake8.pycqa.org/) and [coverage.py](https://coverage.readthedocs.io/).

### Content

- Demo equipment names (MacBook, ThinkPad, Dell XPS and others) are real product names, used only as realistic sample data. Trackroom is not connected to any of these companies.

## Usage of AI

AI tools were used throughout this project as a collaborator, not as a replacement for understanding the code. The table covers the three areas the checklist asks about: debugging, developing features and automated tests.

| Date | Used for | What happened |
|---|---|---|
| 2026-11 | Planning | The rough user stories ("equipment tracker for joiners and leavers, CRUD, manager approves") were rewritten with Claude into 19 MoSCoW stories with acceptance criteria. Claude also suggested the three-model database and the item life cycle (in stock, reserved, assigned, in repair, retired). |
| 2026-11-06 | Planning | Claude reviewed the repository and found that `main` had been reset to the first commit, with the working app only on a local backup branch, and that `main` had no `.gitignore` while `config/env.py` (with the secret key) sat in the folder. The backup was used as the starting point, and a new `.gitignore` was written first. |
| 2026-11-06 | Developing features | Claude Code rebuilt the app around the new stories: split it into `accounts` and `equipment` apps; wrote the models, forms, views, templates and CSS; kept the original Trackroom sidebar design; and upgraded Django 4.2 to 5.2 LTS, because 4.2's security support ended in April 2026. Photo uploads (Cloudinary) were dropped in favour of type icons, which removed an external account and three packages. |
| 2026-11-06 | Automated tests | Claude Code wrote 80 tests from the acceptance criteria. The first run failed 55 of 78 because the new login message crashed when the test client logged in without the message system. It was fixed with `fail_silently`. A faster test-only password hasher cut the run from 4 minutes to 7 seconds. |
| 2026-11-06 | Debugging | A Playwright run in Chrome found a bug the unit tests missed: on the "Change your request" page, the start date box was empty. The UK date format (11/11/2026) does not fit a browser date picker, which needs 2026-11-11, so saving failed. The widget was fixed to always send YYYY-MM-DD, and a test was added that checks the date appears. |
| 2026-11-06 | Debugging | Django's deployment check (`check --deploy`) with `DEBUG=False` found that a new `/favicon.ico` redirect crashed the site at start-up in production, because it looked up a hashed static file name before `collectstatic` had run. It was changed to look the name up only when requested, then a full production rehearsal (collectstatic, gunicorn, HTTPS redirect, security headers, 404 page) was run. |
| 2026-11-06 | Code quality | The browser screenshots showed docks and routers listed before laptops (types were sorted alphabetically), so the catalogue and stock list now list laptops first, with a test. flake8 found 13 long lines, which were fixed. |
| 2026-11-06 | Testing | Every page was sent to the W3C HTML validator (23 pages, 0 errors), the CSS to the W3C CSS validator (0 errors; two old-style rules were also tidied), and every page was audited with axe for WCAG 2.1 AA (0 violations, including phone widths). |

All AI output was reviewed and tested before use: see [TESTING.md](TESTING.md) for the results.

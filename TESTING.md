# Testing

Back to the [README](README.md).

## Summary

| Check | Tool | Result |
|---|---|---|
| Automated tests | Django `TestCase` (`python manage.py test`) | **80 tests, all pass** (about 7 seconds) |
| Code coverage | coverage.py | **97%** of app code (migrations and tests excluded) |
| PEP 8 | flake8 | **0 problems** |
| Missing migrations | `makemigrations --check` | **None** |
| Continuous integration | GitHub Actions (`.github/workflows/ci.yml`) | flake8, migrations check and all tests on every push to `main` |
| HTML | W3C Nu HTML validator | **23 pages, 0 errors, 0 warnings** |
| CSS | W3C CSS validator (Jigsaw) | **0 errors** (3 information-only warnings, explained below) |
| Accessibility | axe-core 4.10 (WCAG 2.0/2.1 A and AA, plus best practice) | **24 page checks, 0 violations** |
| End-to-end journey | Playwright driving Google Chrome | **45 of 45 checks pass** |
| Responsive | Playwright at 320, 375, 768 and 1280px | **No sideways scrolling** on any page checked |
| Production rehearsal | gunicorn with `DEBUG=False`, `collectstatic`, `check --deploy` | Pass (one deliberate warning, explained below) |

## Automated tests

Run them with:

```bash
python manage.py test
```

| File | Tests | What it proves |
|---|---|---|
| `accounts/tests.py` | 9 | Registration creates an employee (never a manager, even if `is_staff` is posted), duplicate emails and mismatched passwords are refused, login and logout show their messages, logout needs POST. |
| `equipment/tests/test_models.py` | 12 | Only in-stock items in good or fair condition are available; the database refuses two pending requests for one item; approve assigns the item; reject needs a reason and returns the item to stock; a request cannot be decided twice; handbacks send items to stock or repair; items with history cannot be deleted; the demo data command is safe to run twice. |
| `equipment/tests/test_employee_views.py` | 30 | Every employee page needs a login; the catalogue shows only available items, laptops first, with type filter and search; requests reserve the item; the employee cannot be faked in the form; one pending request per type; no past start dates; employees see only their own requests; edit and cancel work only while pending and only on their own requests (others get a 404); the edit form shows the saved start date. |
| `equipment/tests/test_manager_views.py` | 29 | Employees get 403 and visitors are sent to login on all 9 manager pages; employees cannot approve or delete by sending a POST directly; stock create, edit and delete with validation; status is locked while assigned; items with history cannot be deleted; filters, search and holder view; approve and reject (reason required); deciding twice shows an error; the admin bulk-approve action; handbacks; the people page; dashboard totals; the custom 404 page. |

**Coverage**

```bash
coverage run --source=accounts,equipment,config manage.py test
coverage report
```

95% of the app code is covered. The lines not covered are production-only settings (the PostgreSQL and HTTPS branches), which are checked by the production rehearsal below instead.

## Manual and browser testing by user story

These were run in Google Chrome through Playwright on 6 November 2026, against a local server loaded with the demo data (`seed_equipment`). Each row is one of the 45 checks in the browser run, or a group of them.

| Story | Test | Expected | Result |
|---|---|---|---|
| EST-01 | Register a new account | Taken to the catalogue, with "Your account has been created" and "You are logged in as ..." | Pass |
| EST-01 | Log in with a wrong password | "Please enter a correct username and password", not logged in | Pass |
| EST-01 | Log in as manager | "You are logged in as manager." and the manager dashboard | Pass |
| EST-01 | Log out | "You have been logged out." | Pass |
| EST-02 | Employee opens `/manage/requests/` | 403 "Managers only" page | Pass |
| EST-02 | Employee opens a request id that is not theirs | 404 page | Pass |
| EST-06 | Choose the Laptop tab | Only laptops; the bad-condition HP EliteBook is hidden | Pass |
| EST-07 | Request the MacBook Air with job title, start date and note | "Request sent for MacBook Air ..." | Pass |
| EST-07 | Request a second laptop | "You already have a pending request for a laptop" plus "Please correct the highlighted fields." | Pass |
| EST-07 | Request a monitor as well | Request sent (different types are allowed) | Pass |
| EST-09 | Swap the laptop request to the Dell XPS 13 | "Your request has been updated." and the list shows the Dell | Pass (after fixing bug 1) |
| EST-10 | Cancel the monitor request | Confirmation page, then "... was cancelled." | Pass |
| EST-11 | Manager opens the request and approves with a note | The employee's note is shown; "Approved. Dell XPS 13 is now assigned to sam.patel." | Pass |
| EST-17 | Filter stock by status "Assigned" | Only the Dell XPS 13 | Pass |
| EST-12 | Record a handback in Bad condition | "Handback recorded" and the item shows "In repair" | Pass |
| EST-03 | Submit an empty Add equipment form | "Please correct the highlighted fields." | Pass |
| EST-03/04/05 | Add, edit and delete a Surface Laptop | "Equipment added to stock.", "Equipment updated.", "... was deleted." | Pass |
| EST-16 | Sideways scrolling at 375px (4 employee pages) and at 320, 375 and 768px (4 manager pages each) | None | Pass (16 checks) |
| EST-16 | Press Tab once on the home page | Focus lands on "Skip to main content" | Pass |

### Responsive screenshots

The README's [Features section](README.md#features) shows each page at desktop, tablet (768px) and phone (375px) widths.

### Browsers and devices

- Google Chrome (desktop, macOS): every check above.
- **Still to do:** Safari on a real iPhone, and Firefox, after the site is deployed.

## Validators

### HTML: W3C Nu validator

Each page's HTML, as rendered for a logged-in user, was sent to https://validator.w3.org/nu/.

| Page | Errors | Warnings |
|---|---|---|
| Home (public), Log in, Register, 404 | 0 | 0 |
| Employee: dashboard, catalogue, request form, my requests, edit request, cancel request, my equipment, 403 | 0 | 0 |
| Manager: dashboard, request queue, decided requests, review request, stock list, item detail, edit item, delete item, handback, add equipment, people | 0 | 0 |

### CSS: W3C Jigsaw validator

`static/css/style.css`: **valid, 0 errors**. Three warnings remain, and none of them is a problem:

- Two say "CSS variables are not statically checked". The validator cannot check `var(--colour)` values; this is normal for any site that uses CSS variables.
- One says "Same colour for background-color and border-color" on the active filter tab. This is on purpose: the active tab is solid blue.

Two earlier warnings were fixed: the old-style `clip: rect()` was replaced with `clip-path: inset(50%)`, and a duplicate system-font name was removed.

### Python: flake8

```bash
flake8 --exclude=.venv,staticfiles,migrations .
```

No problems. Migrations are excluded because Django generates them.

## Accessibility

The axe-core engine (the same engine Lighthouse uses for its accessibility score) was run on every page with the WCAG 2.0 and 2.1 A/AA rules plus best practices, at 1280px, with the home page, my requests and stock list also checked at 375px. **0 violations across 24 checks**, including colour contrast.

Built-in accessibility features: a skip link; a visible yellow focus outline; labels on every form field; Django's `aria-invalid` on fields with errors; `aria-current` on the active page; status shown in words, not colour alone; screen-reader text on repeated buttons ("Edit request for MacBook Air"); and messages announced with `role="status"` or `role="alert"`.

**Still to do after deploying:** run Lighthouse in Chrome DevTools on the live site and add the screenshots here, and try the site with VoiceOver.

## Security and production checks

A copy of the project was run exactly as Heroku runs it: `DEBUG=False`, a random `SECRET_KEY`, `collectstatic`, then gunicorn.

| Check | Result |
|---|---|
| `python manage.py check --deploy` | 1 warning: `SECURE_HSTS_PRELOAD` is not set. This is deliberate. Preloading cannot be used on a `herokuapp.com` address, and it is very hard to undo. |
| Start in production with no `SECRET_KEY` | Refuses to start: "Set a unique SECRET_KEY environment variable for production." |
| Plain HTTP request | 301 redirect to HTTPS |
| `/catalogue/` and `/manage/requests/` logged out | 302 to the login page |
| `/no-such-page/` | Custom 404 page, with no Django debug page |
| Static CSS | Served by WhiteNoise with a hashed file name (200) |
| Headers | `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin` |
| Cookies | CSRF cookie marked `Secure` and `SameSite=Lax` |
| Secrets in git | `config/env.py`, `.env` and `db.sqlite3` are in `.gitignore`. The repository's only earlier commits on GitHub contain no secrets. |

## Bugs found and fixed

| # | Bug | How it was found | Fix |
|---|---|---|---|
| 1 | On "Change your request", the start date box was empty, so saving failed. The UK date format (11/11/2026) is not accepted by a browser date picker, which needs 2026-11-11. | Browser test (the unit tests sent the date directly, so they passed) | The date widget always sends YYYY-MM-DD. A test now checks that the saved date appears in the form. |
| 2 | 55 of the first 78 tests crashed: the "You are logged in" message failed when the test client logged in without the message system. | First test run | The login and logout messages use `fail_silently=True`. |
| 3 | In production, the new `/favicon.ico` redirect crashed the site at start-up, because it looked up a hashed static file before `collectstatic` had run. | `check --deploy` with `DEBUG=False` | The file name is now looked up only when the icon is requested. |
| 4 | Docks and routers were listed before laptops, because types were sorted alphabetically. | Reviewing the screenshots | The catalogue, request form and stock list list laptops first. Test added. |
| 5 | Browsers asked for `/favicon.ico` and got a 404. | Server log during the browser test | Redirect to the SVG icon. |

## Known limits

- Photos of equipment (EST-18) and emails when a request is decided (EST-19) are Could-haves that were not built.
- Approving with the Django admin's bulk action has no note field. Rejecting is only possible on the Requests page, so a reason is always given.

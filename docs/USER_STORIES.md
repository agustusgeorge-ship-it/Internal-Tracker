# Internal Tracker: User Stories

**Version:** 2026-11-06
**What the app does:** an IT equipment tracker for a company. Managers keep a stock list of laptops and other kit and record its condition. New starters sign up and request the equipment they need. A manager approves or rejects each request. When someone leaves, their equipment is handed back and checked in.


---

## 1. Who uses the app

| Role | Who they are | How they get the role |
| --- | --- | --- |
| **Employee** | A new starter, current staff member or leaver | Registers on the site. Every new account is an employee. |
| **Manager** | IT or office manager who controls the stock | A Django superuser/staff account, created with `createsuperuser` or ticked as "staff" in the admin. Never through the public sign-up form. |

## 2. Words used in the stories

- **Equipment:** one physical item with a serial number (a laptop, monitor, phone, headset, dock, router and so on).
- **Equipment type:** Laptop, Monitor, Phone, Peripheral, Infrastructure.
- **Condition:** how good the item is: Good, Fair, Bad (needs repair). Stays with the item.
- **Status:** where the item is in its life: In stock, Reserved (request pending), Assigned (with an employee), In repair, Retired.
- **Request:** an employee asking for an item. Status: Pending, Approved, Rejected. Cancelling a pending request deletes it.
- **Handback:** a leaver returning an item. The manager records the condition it came back in.

## 3. Priority summary (MoSCoW)

| ID | Story | Priority | Epic |
| --- | --- | --- | --- |
| EST-01 | Create an account, log in and log out | Must | Accounts |
| EST-02 | Separate employee and manager access | Must | Accounts |
| EST-03 | Manager adds equipment to stock | Must | Stock |
| EST-04 | Manager updates equipment, including condition | Must | Stock |
| EST-05 | Manager removes equipment from stock | Must | Stock |
| EST-06 | Employee browses available equipment | Must | Requests |
| EST-07 | Employee requests equipment (Create) | Must | Requests |
| EST-08 | Employee views their requests (Read) | Must | Requests |
| EST-09 | Employee changes a pending request (Update) | Must | Requests |
| EST-10 | Employee cancels a pending request (Delete) | Must | Requests |
| EST-11 | Manager approves or rejects a request | Must | Approvals |
| EST-12 | Leaver hands equipment back | Must | Handback |
| EST-13 | Manager dashboard | Should | Reporting |
| EST-14 | Employee sees the equipment they hold | Should | Requests |
| EST-15 | Clear success and error messages | Should | UX |
| EST-16 | Responsive and accessible pages | Should | UX |
| EST-17 | Search and filter the stock list | Could | Stock |
| EST-18 | Equipment photos | Could | Stock |
| EST-19 | Email when a request is decided | Could | Approvals |
| — | Barcode scanning, HR system link, multiple offices | Won't (this version) | — |

**Where the CRUD marks come from:** the employee does full CRUD on their own **requests** from the front end (EST-07 to EST-10). The manager does full CRUD on **equipment** (EST-03 to EST-05). Approval is an extra business rule on top (EST-11).

---

## 4. The stories

### EST-01: Create an account, log in and log out

**Priority:** Must · **Epic:** Accounts · **Project goal:** LO3 Authentication

**User story:** As a **new employee**, I can **create an account and log in** so that **I can choose the equipment I need for my job**.

**Acceptance criteria**
- [ ] A visitor can register with a username, email address and password (entered twice).
- [ ] Django's password rules are applied, and errors are shown next to the field that caused them.
- [ ] A new account is always an employee: the sign-up form cannot create a manager.
- [ ] After registering, the employee is logged in and taken to the equipment catalogue.
- [ ] A registered user can log in and log out. Logout uses a POST form with CSRF protection.
- [ ] The navigation bar shows who is logged in and whether they are an employee or a manager.

**Implementation notes:** `accounts.views.RegisterView` with `RegistrationForm`; login and logout use Django's own views. Messages come from `accounts/signals.py`.

---

### EST-02: Separate employee and manager access

**Priority:** Must · **Epic:** Accounts · **Project goal:** LO3 Authorisation

**User story:** As a **manager**, I want **employees to only see and change their own requests** so that **stock and approvals stay under my control**.

**Acceptance criteria**
- [ ] Employees cannot add, edit or delete equipment.
- [ ] Employees can only see their own requests, even if they type another request's URL (they get a 404).
- [ ] Only managers (staff users) can open `/admin/` and approve or reject requests.
- [ ] Every rule is checked in the view on the server, not just by hiding buttons.
- [ ] Logged-out visitors are sent to the login page when they open any page except home, login and register.

**Implementation notes:** Use `request.user.is_staff` as the manager check. Use `LoginRequiredMixin` for employees and `UserPassesTestMixin` (or `staff_member_required`) for manager pages. Filter requests with `.filter(employee=request.user)`.

---

### EST-03: Manager adds equipment to stock

**Priority:** Must · **Epic:** Stock · **Project goal:** LO2 CRUD (Create), LO7 Data model

**User story:** As a **manager**, I can **add a piece of equipment to the stock list** so that **it can be given to someone who needs it**.

**Acceptance criteria**
- [ ] The form has: name/model, serial number, equipment type, condition, location and notes.
- [ ] Name, serial number and type are required. The serial number must be unique.
- [ ] New equipment starts with the status **In stock**.
- [ ] If the form has errors, nothing is saved, the typed values stay in the form and each error is shown by its field.
- [ ] After saving, the manager sees a confirmation message.

**Implementation notes:** The `Equipment` model already exists. Add an `equipment_type` field (choices: Laptop, Monitor, Phone, Peripheral, Infrastructure), a `status` field (see section 2) and an `assigned_to` field (ForeignKey to User, can be blank). Equipment is now owned by the company, not by the person who typed it in. Manage it in Django admin, or on a staff-only front-end page.

---

### EST-04: Manager updates equipment, including condition

**Priority:** Must · **Epic:** Stock · **Project goal:** LO2 CRUD (Update)

**User story:** As a **manager**, I can **update an item's details and mark it as in good or bad condition** so that **we never hand out broken equipment**.

**Acceptance criteria**
- [ ] The manager can change any field, including condition and location.
- [ ] Items in **Bad** condition cannot be requested by employees.
- [ ] The same validation as EST-03 applies when editing.
- [ ] The list shows the condition as text as well as colour (for example a badge reading "Bad"), so it does not rely on colour alone.

---

### EST-05: Manager removes equipment from stock

**Priority:** Must · **Epic:** Stock · **Project goal:** LO2 CRUD (Delete)

**User story:** As a **manager**, I can **remove an item that has been lost or scrapped** so that **the stock list stays accurate**.

**Acceptance criteria**
- [ ] The manager is asked to confirm before anything is deleted.
- [ ] An item that is currently **Assigned** to someone cannot be deleted. The manager is told to record the handback first.
- [ ] Optional: instead of deleting, the manager can set the status to **Retired** so the history is kept.

---

### EST-06: Employee browses available equipment

**Priority:** Must · **Epic:** Requests · **Project goal:** LO1 UX, LO2 Read

**User story:** As a **new employee**, I can **see a list of the equipment available to me** so that **I can pick the laptop and kit I prefer**.

**Acceptance criteria**
- [ ] The catalogue only shows items that are **In stock** and in **Good** or **Fair** condition.
- [ ] Each item shows its name, type and condition.
- [ ] The employee can filter by equipment type (for example "Laptops only").
- [ ] Each item has a **Request this** button.
- [ ] If nothing is available, the page says so clearly instead of showing an empty table.

---

### EST-07: Employee requests equipment (Create)

**Priority:** Must · **Epic:** Requests · **Project goal:** LO2 CRUD (Create)

**User story:** As a **new employee**, I can **request one or more pieces of equipment for my job** so that **it is ready for me on my first day**.

**Acceptance criteria**
- [ ] The request form asks for: the item, my start date and an optional note (for example "I'm left-handed, I need a vertical mouse").
- [ ] I can make separate requests for different types (laptop, monitor, headset), which gives me "a multiple choice of hardware".
- [ ] I cannot request an item that is already reserved or assigned to someone else.
- [ ] I cannot have two open requests for the same type (for example two pending laptops).
- [ ] A new request has the status **Pending** and the item becomes **Reserved** so no one else can take it.
- [ ] After submitting, I see a confirmation message and my request list.

**Implementation notes:** New model `EquipmentRequest`: `employee` (FK User), `equipment` (FK Equipment), `start_date`, `note`, `job_title`, `status` (Pending, Approved, Rejected), `manager_note`, `reviewed_by` (FK User, blank), `reviewed_at`, `created_at`. Set `employee = request.user` in the view and never take it from the form.

---

### EST-08: Employee views their requests (Read)

**Priority:** Must · **Epic:** Requests · **Project goal:** LO2 CRUD (Read)

**User story:** As an **employee**, I can **see all my requests and whether they are pending, approved or rejected** so that **I know what is happening with my equipment**.

**Acceptance criteria**
- [ ] "My requests" lists only my own requests, newest first.
- [ ] Each row shows the item, the date I asked, the status and the manager's note if there is one.
- [ ] A rejected request shows the manager's reason.
- [ ] If I have no requests, the page links me to the catalogue.

---

### EST-09: Employee changes a pending request (Update)

**Priority:** Must · **Epic:** Requests · **Project goal:** LO2 CRUD (Update)

**User story:** As an **employee**, I can **change my choice while my request is still pending** so that **I can swap to a different laptop if I change my mind**.

**Acceptance criteria**
- [ ] I can edit the item, start date and note only while the status is **Pending**.
- [ ] Once a request is approved or rejected, the Edit button is gone and the edit URL returns an error message (or 404).
- [ ] If I swap items, the old item goes back to **In stock** and the new one becomes **Reserved**.
- [ ] I cannot edit someone else's request (404).

---

### EST-10: Employee cancels a pending request (Delete)

**Priority:** Must · **Epic:** Requests · **Project goal:** LO2 CRUD (Delete)

**User story:** As an **employee**, I can **cancel my request while it is pending** so that **the item is freed up for someone else**.

**Acceptance criteria**
- [ ] I am asked to confirm before the request is cancelled.
- [ ] Cancelling only works on **Pending** requests.
- [ ] After cancelling, the item goes back to **In stock**.
- [ ] I see a confirmation message and return to "My requests".
- [ ] I cannot cancel someone else's request (404).

**Implementation notes:** Cancelling deletes the request row (the Delete in CRUD) and puts the item back in stock.

---

### EST-11: Manager approves or rejects a request

**Priority:** Must · **Epic:** Approvals · **Project goal:** LO2 Business logic, LO3 Authorisation

**User story:** As a **manager**, I can **approve or reject an employee's equipment choice** so that **people get the right equipment for their role**.

**Acceptance criteria**
- [ ] The manager sees all **Pending** requests, with the oldest or soonest start date first.
- [ ] **Approve:** the request becomes **Approved**, the item becomes **Assigned**, and `assigned_to` is set to the employee.
- [ ] **Reject:** the manager must give a reason. The request becomes **Rejected** and the item goes back to **In stock**.
- [ ] The system records who made the decision and when.
- [ ] A decided request cannot be approved or rejected a second time.
- [ ] Employees cannot reach this feature at all.

**Implementation notes:** Built as a staff-only front-end page (`/manage/requests/<id>/`) with Approve and Reject forms (POST with CSRF). The Django admin also has a bulk "Approve selected" action for the back office.

---

### EST-12: Leaver hands equipment back

**Priority:** Must · **Epic:** Handback · **Project goal:** LO2 Business logic

**User story:** As a **manager**, I can **record that a leaver has handed back their equipment and what condition it is in** so that **it can be checked and reused for the next new starter**.

**Acceptance criteria**
- [ ] The manager can see everything currently assigned to a given employee.
- [ ] The manager can mark an item as returned and record its condition on return (Good, Fair or Bad).
- [ ] An item returned in **Good** or **Fair** condition goes back to **In stock**. An item returned in **Bad** condition goes to **In repair**.
- [ ] `assigned_to` is cleared when the item is returned.
- [ ] The return date is saved so there is a history of who had what.

**Implementation notes:** Built as a staff-only form (`/manage/equipment/<id>/handback/`) that saves a `Handback` record, so each item keeps a full history.

---

### EST-13: Manager dashboard

**Priority:** Should · **Epic:** Reporting · **Project goal:** LO1 UX

**User story:** As a **manager**, I can **see a summary when I log in** so that **I know what needs my attention today**.

**Acceptance criteria**
- [ ] It shows counts for: pending requests, items in stock, items assigned and items in repair or in Bad condition.
- [ ] It lists new starters with a start date in the next 14 days whose requests are still pending.
- [ ] Each count links to the matching filtered list.

**Implementation notes:** `equipment.views.manager_dashboard_context`.

---

### EST-14: Employee sees the equipment they hold

**Priority:** Should · **Epic:** Requests

**User story:** As an **employee**, I can **see a list of equipment assigned to me** so that **I know what I'll need to hand back if I leave**.

**Acceptance criteria**
- [ ] "My equipment" shows every item where `assigned_to` is me, with its serial number.
- [ ] Items I've already handed back no longer appear.

---

### EST-15: Clear success and error messages

**Priority:** Should · **Epic:** UX · **Project goal:** LO1

**User story:** As a **user**, I get **a clear message after every action** so that **I know whether it worked**.

**Acceptance criteria**
- [ ] Success messages appear for register, request, edit, cancel, approve, reject and handback.
- [ ] Failed actions never show a success message.
- [ ] Screen readers announce the messages (`role="status"` or `aria-live`).

**Implementation notes:** Django messages, shown in `templates/base.html`.

---

### EST-16: Responsive and accessible pages

**Priority:** Should · **Epic:** UX · **Project goal:** LO1

**User story:** As a **user on a phone, tablet or laptop**, I can **use every page comfortably** so that **I can request equipment from any device**.

**Acceptance criteria**
- [ ] Pages work at 375px, 768px and 1280px wide, with no sideways scrolling.
- [ ] Everything can be used with the keyboard alone, and focus is clearly visible.
- [ ] Every form field has a label.
- [ ] Lighthouse accessibility score of 90 or more, with screenshots in the README.

---

### EST-17: Search and filter the stock list (Could)

**User story:** As a **manager**, I can **search by name or serial number and filter by type, condition and status** so that **I can find an item quickly**.

**Acceptance criteria**
- [ ] Search matches name or serial number.
- [ ] Filters can be combined, and the search text stays in the box after searching.

**Implementation notes:** `StockListView` (front end) plus `list_filter` and `search_fields` in the admin.

---

### EST-18: Equipment photos (Could)

**User story:** As an **employee**, I can **see a photo of each laptop** so that **I can choose the one I prefer**.

**Status:** Not built in this version. Each type has an icon instead, which avoids an external image-hosting account.

---


## 5. Data model (for the README's database section)

```
User (Django built-in)
  is_staff = True  -> Manager
  is_staff = False -> Employee

Equipment
  name, serial_number (unique), equipment_type, condition, status,
  specification, location, notes,
  assigned_to -> User (blank), created_at, updated_at

EquipmentRequest
  employee -> User, equipment -> Equipment,
  start_date, note, job_title, status (Pending/Approved/Rejected),
  manager_note, reviewed_by -> User (blank), reviewed_at, created_at

Handback (gives each item a history)
  equipment -> Equipment, employee -> User,
  returned_on, condition_on_return, checked_by -> User
```

**Relationships:** one employee has many requests. One piece of equipment has many requests over its life, but only one active request at a time. One piece of equipment is assigned to zero or one employee.

## 6. How an item moves through the system

```
In stock --(employee requests)--> Reserved --(manager approves)--> Assigned
   ^                                  |                               |
   |----(rejected or cancelled)-------+                               |
   |                                                                  |
   +----(handed back: Good/Fair)----------------------- (leaver) -----+
                                    (handed back: Bad) --> In repair --(fixed)--> In stock
```

## 7. Build order and status

| Order | Stories | Status |
| --- | --- | --- |
| 1 | EST-01, EST-02: accounts and roles | Done |
| 2 | EST-03 to EST-05: stock CRUD | Done |
| 3 | EST-06, EST-07: catalogue and requests | Done |
| 4 | EST-08 to EST-10: view, edit and cancel requests | Done |
| 5 | EST-11: approve and reject | Done |
| 6 | EST-12: handbacks | Done |
| 7 | EST-13 to EST-17: dashboards, my equipment, messages, responsive, search | Done |
| 8 | EST-18: photos | Not built (Could) |

Every Must story has automated tests: see [TESTING.md](../TESTING.md).

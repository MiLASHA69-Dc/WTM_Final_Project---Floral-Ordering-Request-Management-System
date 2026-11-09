# BloomBuds: Floral Ordering Request Management System

A Django web application that lets customers browse flowers, submit Quick or Scheduled pickup orders, and track them, while florists review and manage the requests. Built by a three-person team for the WTM Backend Development track (Tech Mentorship Program 2026).

## Features
- User registration, login, and logout
- Flower catalog with search and category filtering
- Session-based shopping cart that survives login
- Quick Orders (same-day pickup before 11:00 AM) and Scheduled Orders
- My Orders page, with revision of orders marked Changes Required
- Florist dashboard: accept, reject, request changes, update status
- Flower and category management (staff only)

## Tech stack
Python, Django, SQLite, HTML/CSS, Django test framework

## Setup (Windows)
1. Clone the repository and open the folder.
2. Create and activate a virtual environment:
   python -m venv venv
   venv\Scripts\activate
3. Install dependencies:
   pip install -r requirements.txt
4. Create the database:
   python manage.py migrate
5. Load sample flowers [check the fixture path]:
   python manage.py loaddata fixtures/sample_flowers.json
6. Create a staff account:
   python manage.py createsuperuser
7. Start the server:
   python manage.py runserver
8. Open http://127.0.0.1:8000/

Flower images are not stored in Git. To show images, upload them for each flower in the admin at /admin/ (sample images are in fixtures/sample_images/).

## Running the tests
python manage.py test
38 tests: 14 shopping cart and 24 order management.

## Main pages
| URL | Purpose |
|---|---|
| / | Homepage |
| /catalog/ | Customer flower catalog |
| /cart/ | Shopping cart |
| /accounts/login/, /accounts/register/ | Authentication |
| /orders/ | Customer orders |
| /catalog/florist/dashboard/ | Florist dashboard (staff) |
| /catalog/management/ | Flower and category management (staff) |
| /admin/ | Django admin (staff) |

## Team
| Member | Module |
|---|---|
| Milasha Ninnadi Subasinghe (Team Lead) | Order management |
| Stephanie Simon | Authentication, catalog browsing, session cart |
| Grace Iliya Rishama | Florist management, flower and category CRUD |

## Limitations
Single-shop prototype running locally. Pickup only, with payment at the shop. No online payments, delivery, or automatic stock reservation. The cart is cleared if cookies are cleared.
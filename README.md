# GreenPaws E-commerce MVP

A responsive no-build e-commerce storefront and admin dashboard for pet food and plant seeds.

## Run with permanent database

Install Python 3.10+ from [python.org](https://www.python.org/downloads/) and tick **Add Python to PATH** during installation. Then open a terminal in this folder and run:

```powershell
python server.py
```

Open `http://localhost:8000` for the storefront and `http://localhost:8000/admin.html` for the admin dashboard. The database is automatically created as `greenpaws.db`; do not delete it, because it contains the products, orders and customer history.

## Included

- Responsive product catalogue, search, category filters, sorting and product details
- Cart, quantities, coupon (`GREEN10`), shipping, demo checkout, COD/bKash/Nagad/SSLCommerz choices
- Checkout customer records, order ID tracking, and order status updates
- Admin sales/order/product/inventory views, CSV export and print-to-PDF
- Python + SQLite permanent database for products, stock, orders, customers and purchase history
- Admin dashboard that reads real saved data, changes order status and adds products

## Production work still required

Connect a backend/database, real payment-gateway credentials/webhooks, image storage, authentication and role permissions, email/SMS services, and a dedicated heatmap/session-recording provider.

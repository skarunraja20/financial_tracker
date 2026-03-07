# Financial Portfolio Tracker

A **secure, offline-first personal finance application** designed to help individuals track their complete financial portfolio in one place.
The application consolidates **assets, liabilities, insurance records, and contacts**, providing a clear view of overall **net worth and financial health**.

---

## Key Features

### 1. Comprehensive Asset Portfolio Tracking

Track all major investment categories in one place:

* Provident Fund (PF)
* Fixed Deposits
* Bonds
* Debt & Equity Mutual Funds
* Stocks (NSE/BSE)
* Gold Mutual Funds
* Sovereign Gold Bonds (SGB)
* Real Estate properties

Each asset displays:

* Invested Amount
* Current Value
* Gain / Loss in real-time

This provides a unified view of your entire investment portfolio.

---

### 2. Liabilities & Loan Management

Record and monitor all outstanding loans, including:

* Home Loans
* Personal Loans
* Gold Loans
* Mutual Fund-backed Loans

For each liability, you can track:

* Principal Amount
* EMI
* Interest Rate
* Outstanding Balance

This allows you to accurately calculate **net worth after liabilities**.

---

### 3. Net Worth Dashboard

The application dashboard aggregates all assets and liabilities into a single **net worth figure**.

Features include:

* Indian number formatting (K / L / Cr)
* KPI cards for each asset category
* Pie charts showing asset allocation
* Bar charts displaying portfolio growth trends

This provides an **instant snapshot of financial health**.

---

### 4. Records — Investments, Insurance & Contacts

The **Records section** includes three dedicated tabs:

#### Investments

Log investment activity including:

* SIP transactions
* Lump-sum investments
* Investment platform details

#### Protection & Insurance

Store and manage insurance details such as:

* Policy Numbers
* Premium Amounts
* Coverage Value
* Renewal Dates

#### Contacts

Maintain a directory of financial contacts:

* Advisors
* Brokers
* Bank representatives

All records can be **exported to a structured Excel file**.

---

### 5. Excel Export with Professional Formatting

Every Records tab supports **one-click Excel export**.

Generated spreadsheets include:

* Navy-colored header row
* Alternating pale-blue and white data rows
* Clear, readable formatting
* Ready-to-share professional reports

---

### 6. Bulk Import via CSV / Excel

Supported asset categories such as **Mutual Funds and Stocks** allow **bulk data import**.

Features include:

* Import from CSV or Excel files
* Guided Import Wizard
* Fast portfolio onboarding for large datasets

This eliminates manual entry for extensive portfolios.

---

### 7. Reports & Portfolio Charts

The **Reports section** provides analytical insights into your portfolio.

Capabilities include:

* Tabular summary across all asset classes
* Asset allocation donut chart
* Category-wise bar charts
* Historical net-worth trend

Charts are generated using **Matplotlib** and rendered locally without internet connectivity.

---

### 8. Secure, Fully Offline & Portable

The application is designed with **security and privacy as top priorities**.

Security features include:

* Local **SQLite database**
* **bcrypt-hashed passwords**
* **AES-256-GCM encryption** for sensitive fields (account numbers, folios)

Operational advantages:

* No internet connection required
* No cloud account needed
* Fully **offline and portable**

To run the application:

1. Extract the ZIP file on any Windows laptop
2. Open the application folder
3. Double-click the launcher to start

Your financial data **remains fully under your control**.

---

## Technology Stack

* Python
* SQLite
* Matplotlib
* Pandas
* bcrypt
* AES-256-GCM encryption

---

## Use Cases

This tool is ideal for:

* Individual investors managing diversified portfolios
* Financial planners tracking client portfolios offline
* Users who prefer **privacy-first financial management**

---

## Disclaimer

This application is intended for **personal financial tracking and informational purposes only**.
It does not provide investment advice or financial recommendations.

---

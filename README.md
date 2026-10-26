# Cloud-Based Real-Time Collaboration Platform

A compact Flask application for a college AWS cloud-computing project. It implements six basic modules:
1. Authentication and Admin/Member roles
2. Workspaces and membership
3. Task management and assignment
4. Document upload/list/download/delete
5. Shared discussion board (HTTP refresh; not WebSocket real-time)
6. Task analytics dashboard

## Zero-budget development mode
The app defaults to SQLite and local file uploads, so you can build and test without creating paid AWS resources. AWS S3 is optional via environment variables. For a cloud deployment, you can configure an eligible AWS free-tier environment only after checking current pricing and your account eligibility. Free tier is not a guarantee of zero charges.

## Requirements
- Python 3.11+
- Git
- Internet for installing Python packages and Bootstrap CDN

## Windows setup (PowerShell)
```powershell
cd cloud-collaboration-platform
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```
Edit `.env` and change `SECRET_KEY` and `INITIAL_ADMIN_PASSWORD`.

Run:
```powershell
python app.py
```
Open http://127.0.0.1:5000

If PowerShell blocks activation, use CMD:
```bat
.venv\Scripts\activate.bat
```

## Demo accounts
On first run, the initial admin is created using `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` from `.env`. Sign in with those credentials and change the password immediately by editing `.env` and deleting the local database only if you are still in development and have no data to preserve. Do not use the example password on a public server.

New accounts created through the registration page receive the Member role. Admins can promote/demote users in the Users page.

## Optional S3
1. Create a private S3 bucket only after checking your account's charges/free-tier eligibility.
2. Give the application's AWS identity permission only to the required bucket actions (GetObject, PutObject, DeleteObject, ListBucket as needed).
3. Set `S3_BUCKET` and `AWS_REGION` in `.env`.
4. For local development, configure AWS credentials using an approved AWS CLI profile; never put access keys in source code or `.env` committed to GitHub. On EC2, prefer an instance role.
5. Files uploaded when S3 is configured are stored in S3. The app stores the object key and metadata in SQLite/RDS.

## Optional RDS MySQL
The app accepts `DATABASE_URL`. Example format:
`mysql+pymysql://USERNAME:PASSWORD@HOST:3306/DATABASE_NAME`
Use URL-encoding for special characters in passwords. Keep credentials in environment variables, configure RDS networking securely, and never expose the database publicly.

## Security notes
- Passwords are hashed.
- Login-protected pages and role checks are used.
- CSRF protection is enabled for Flask-WTF forms.
- Uploaded files are limited to 10 MB and use generated storage keys.
- This is a student project starter, not a security-audited production service.
- Do not upload sensitive/private documents to a public demo.
- Configure HTTPS and a secure secret key before public deployment.

## Important project-scope note
The discussion board uses ordinary HTTP requests and page refreshes. It is shared messaging, not Google Docs-style simultaneous editing or WebSocket messaging.

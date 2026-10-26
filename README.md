# Cloud-Based Real-Time Collaboration Platform

A web-based collaboration platform designed to help teams organize workspaces, manage tasks, share documents, communicate through discussions, and monitor project progress in one place.

## Overview

The Cloud-Based Real-Time Collaboration Platform provides a centralized workspace for project teams. Users can organize projects, assign tasks, exchange messages through a shared discussion board, manage documents, and track progress through a dashboard.

The project demonstrates the development of a modular web application with user authentication, workspace management, task tracking, document handling, team discussions, and project analytics.

## Features

### 1. User Authentication and Role Management
- User registration and login.
- Authenticated access to application features.
- Role-based access for supported administrative operations.

### 2. Workspace Management
- Create and manage workspaces.
- Organize team members within workspaces.
- Keep project activities associated with the relevant workspace.

### 3. Task Management
- Create, edit, and delete tasks.
- Assign tasks to workspace members.
- Track task status and priorities.
- Monitor task completion.

### 4. Document Management
- Upload and manage project documents.
- Access and download stored files.
- Delete documents when required.

### 5. Team Discussions
- Share messages and updates within a workspace.
- Maintain a shared discussion area for project communication.
- Retrieve discussions through standard application requests.

### 6. Project Analytics
- View task and project progress.
- Monitor task completion and outstanding work.
- Use dashboard summaries to understand project status.

## Technology Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, Bootstrap, JavaScript
- **Database:** SQLite for local development, with optional database configuration
- **Authentication:** Flask-Login
- **ORM:** Flask-SQLAlchemy
- **Forms and validation:** Flask-WTF
- **Version control:** Git and GitHub

### AWS Integration and Deployment

The project is intended to demonstrate cloud deployment concepts. Potential AWS integrations include:

- **Amazon EC2:** Host the Flask application.
- **Amazon RDS:** Store application data in a managed relational database.
- **Amazon S3:** Store project documents.
- **AWS IAM:** Manage permissions for AWS resources.
- **Amazon CloudWatch:** Collect application logs and monitor deployed resources.

These AWS services should be considered planned or optional integrations unless they have been configured and tested in the deployed application.

## Architecture

```text
User / Web Browser
        |
        v
Frontend Interface
(HTML, CSS, Bootstrap, JavaScript)
        |
        v
Flask Application
        |
        +------ User Authentication
        +------ Workspace Management
        +------ Task Management
        +------ Document Management
        +------ Team Discussions
        +------ Project Analytics
        |
        v
Database and File Storage
(SQLite and local storage in the default
local development configuration)
```

The architecture can be extended to use managed AWS database and object-storage services for cloud deployment.

## Getting Started

### Prerequisites

- Python 3.10 or a compatible Python version.
- Git.
- pip.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/cloud-based-collaboration-platform.git
cd cloud-based-collaboration-platform
```

Replace `YOUR-USERNAME` with your GitHub username.

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use the Command Prompt activation script instead:

```bat
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root using the provided `.env.example` as a starting point, if available.

Set the required values for your local setup, including a secret key and the initial administrator credentials if these are supported by the current configuration.

**Do not commit `.env` or real passwords to GitHub.**

### 5. Start the application

```bash
python app.py
```

Open the local address printed in the terminal, typically:

`http://127.0.0.1:5000`

Follow the application's registration and login flow to explore the available modules.

## Project Structure

```text
cloud-based-collaboration-platform/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── templates/
├── static/              # If included in the project
├── uploads/             # Local uploaded files; not committed
└── README.md
```

The exact contents may vary with the current version of the project.

## Testing

The local application has been tested for the following modules:

- User authentication and role management.
- Workspace management.
- Task management.
- Document management.
- Team discussions.
- Project analytics.

Cloud deployment and individual AWS service integrations require separate verification.

## Current Limitations

- The default setup is intended for local development.
- The discussion module uses standard application requests; it does not imply WebSocket-based live synchronization.
- Cloud hosting, managed database storage, and cloud document storage must be configured separately before they can be claimed as deployed features.
- Production use would require additional deployment, security, backup, and monitoring configuration.

## Future Enhancements

- Deploy the application to an appropriate cloud environment.
- Integrate Amazon RDS and Amazon S3.
- Configure IAM roles and CloudWatch monitoring.
- Improve notification functionality.
- Add automated tests and production deployment workflows.

## Learning Outcomes

This project demonstrates practical experience with Python web development, authentication, relational data modeling, CRUD operations, file handling, modular application design, version control, and cloud architecture concepts.

## Author

**Your Name**

Computer Science and Engineering

## License

Choose and add an appropriate open-source license if you intend to distribute the project under one.

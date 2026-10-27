import os
import uuid
from datetime import datetime, date
import re
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from flask import (
    Flask, render_template, redirect, url_for, flash, request, abort,
    send_from_directory, current_app
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, ValidationError

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
db_url = os.getenv("DATABASE_URL", "sqlite:///collaboration.db")
if db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH_MB", "10")) * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")
app.config["S3_BUCKET"] = os.getenv("S3_BUCKET", "").strip()
app.config["AWS_REGION"] = os.getenv("AWS_REGION", "ap-south-1")
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

workspace_members = db.Table(
    "workspace_members",
    db.Column("workspace_id", db.Integer, db.ForeignKey("workspace.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Member")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Workspace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), default="")
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    creator = db.relationship("User", foreign_keys=[created_by])
    members = db.relationship("User", secondary=workspace_members, backref="workspaces")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspace.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    due_date = db.Column(db.Date, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    creator = db.relationship("User", foreign_keys=[created_by])
    workspace = db.relationship("Workspace", backref="tasks")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspace.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    author = db.relationship("User")
    workspace = db.relationship("Workspace", backref="messages")

class StoredFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspace.id"), nullable=False, index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False)
    storage_type = db.Column(db.String(20), nullable=False, default="local")
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    uploader = db.relationship("User")
    workspace = db.relationship("Workspace", backref="files")

def validate_email_format(form, field):
    """Validate basic email syntax without the optional email_validator package."""
    email = (field.data or "").strip()
    if len(email) > 180 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValidationError("Enter a valid email address.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), validate_email_format])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField(
        "Email",
        validators=[DataRequired(), validate_email_format, Length(max=180)],
    )
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create account")

class WorkspaceForm(FlaskForm):
    name = StringField("Workspace name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Create workspace")

class TaskForm(FlaskForm):
    title = StringField("Task title", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Description", validators=[Optional()])
    assigned_to = SelectField("Assign to", coerce=int, validators=[Optional()])
    priority = SelectField("Priority", choices=[("Low", "Low"), ("Medium", "Medium"), ("High", "High")])
    status = SelectField("Status", choices=[("Pending", "Pending"), ("In Progress", "In Progress"), ("Completed", "Completed")])
    due_date = DateField("Due date", validators=[Optional()])
    submit = SubmitField("Save task")

class MessageForm(FlaskForm):
    body = TextAreaField("Message", validators=[DataRequired(), Length(min=1, max=2000)])
    submit = SubmitField("Post message")

class AddMemberForm(FlaskForm):
    user_id = SelectField("Member", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Add member")

class RoleForm(FlaskForm):
    role = SelectField("Role", choices=[("Member", "Member"), ("Admin", "Admin")])
    submit = SubmitField("Update role")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def s3_client():
    return boto3.client("s3", region_name=app.config["AWS_REGION"])

def is_admin():
    return current_user.is_authenticated and current_user.role == "Admin"

def get_workspace_or_404(workspace_id):
    workspace = db.session.get(Workspace, workspace_id)
    if not workspace:
        abort(404)
    if not is_admin() and current_user not in workspace.members:
        abort(403)
    return workspace

def admin_required():
    if not is_admin():
        abort(403)

def init_db():
    with app.app_context():
        db.create_all()
        admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com").strip().lower()
        admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "ChangeThisNow123!")
        if not User.query.filter_by(email=admin_email).first():
            admin = User(name="Project Admin", email=admin_email, role="Admin")
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"[Initial admin created] Email: {admin_email}. Change the initial password before any public deployment.")

@app.context_processor
def inject_helpers():
    return {"today": date.today(), "is_admin": is_admin}

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "warning")
        else:
            user = User(name=form.name.data.strip(), email=email, role="Member")
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created. Welcome!", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    if is_admin():
        workspace_ids = [w.id for w in Workspace.query.all()]
    else:
        workspace_ids = [w.id for w in current_user.workspaces]
    tasks_query = Task.query.filter(Task.workspace_id.in_(workspace_ids)) if workspace_ids else Task.query.filter(False)
    total = tasks_query.count()
    completed = tasks_query.filter_by(status="Completed").count()
    pending = tasks_query.filter(Task.status != "Completed").count()
    overdue = tasks_query.filter(Task.due_date.isnot(None), Task.due_date < date.today(), Task.status != "Completed").count()
    workspaces = Workspace.query.order_by(Workspace.created_at.desc()).all() if is_admin() else sorted(current_user.workspaces, key=lambda w: w.created_at, reverse=True)
    recent_tasks = tasks_query.order_by(Task.created_at.desc()).limit(8).all()
    return render_template("dashboard.html", workspaces=workspaces, total=total, completed=completed, pending=pending, overdue=overdue, recent_tasks=recent_tasks)

@app.route("/workspaces", methods=["GET", "POST"])
@login_required
def workspaces():
    form = WorkspaceForm()
    if form.validate_on_submit():
        workspace = Workspace(name=form.name.data.strip(), description=(form.description.data or "").strip(), created_by=current_user.id)
        workspace.members.append(current_user)
        db.session.add(workspace)
        db.session.commit()
        flash("Workspace created.", "success")
        return redirect(url_for("workspace_detail", workspace_id=workspace.id))
    items = Workspace.query.order_by(Workspace.created_at.desc()).all() if is_admin() else sorted(current_user.workspaces, key=lambda w: w.created_at, reverse=True)
    return render_template("workspaces.html", form=form, workspaces=items)

@app.route("/workspaces/<int:workspace_id>")
@login_required
def workspace_detail(workspace_id):
    workspace = get_workspace_or_404(workspace_id)
    tasks = Task.query.filter_by(workspace_id=workspace.id).order_by(Task.created_at.desc()).all()
    messages = Message.query.filter_by(workspace_id=workspace.id).order_by(Message.created_at.asc()).all()
    files = StoredFile.query.filter_by(workspace_id=workspace.id).order_by(StoredFile.uploaded_at.desc()).all()
    return render_template("workspace_detail.html", workspace=workspace, tasks=tasks, messages=messages, files=files)

@app.route("/workspaces/<int:workspace_id>/members", methods=["GET", "POST"])
@login_required
def members(workspace_id):
    workspace = get_workspace_or_404(workspace_id)
    if not (is_admin() or workspace.created_by == current_user.id):
        abort(403)
    form = AddMemberForm()
    existing_ids = [u.id for u in workspace.members]
    candidates = User.query.filter(~User.id.in_(existing_ids)).order_by(User.name).all() if existing_ids else User.query.order_by(User.name).all()
    form.user_id.choices = [(u.id, f"{u.name} ({u.email})") for u in candidates]
    if form.validate_on_submit():
        user = db.session.get(User, form.user_id.data)
        if user and user not in workspace.members:
            workspace.members.append(user)
            db.session.commit()
            flash("Member added to workspace.", "success")
            return redirect(url_for("workspace_detail", workspace_id=workspace.id))
        flash("Choose a valid user.", "warning")
    return render_template("members.html", workspace=workspace, form=form, candidates=candidates)

@app.route("/workspaces/<int:workspace_id>/tasks/new", methods=["GET", "POST"])
@login_required
def task_new(workspace_id):
    workspace = get_workspace_or_404(workspace_id)
    form = TaskForm()
    form.assigned_to.choices = [(0, "Unassigned")] + [(u.id, u.name) for u in workspace.members]
    form.status.data = "Pending"
    if form.validate_on_submit():
        assignee_id = form.assigned_to.data or None
        allowed = {u.id for u in workspace.members}
        if assignee_id and assignee_id not in allowed:
            flash("Assignee must belong to this workspace.", "danger")
            return render_template("task_form.html", form=form, workspace=workspace, heading="Create task")
        task = Task(
            workspace_id=workspace.id, title=form.title.data.strip(),
            description=(form.description.data or "").strip(), assigned_to=assignee_id,
            priority=form.priority.data, status=form.status.data,
            due_date=form.due_date.data, created_by=current_user.id
        )
        db.session.add(task)
        db.session.commit()
        flash("Task created.", "success")
        return redirect(url_for("workspace_detail", workspace_id=workspace.id))
    return render_template("task_form.html", form=form, workspace=workspace, heading="Create task")

@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def task_edit(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        abort(404)
    workspace = get_workspace_or_404(task.workspace_id)
    form = TaskForm(obj=task)
    form.assigned_to.choices = [(0, "Unassigned")] + [(u.id, u.name) for u in workspace.members]
    if request.method == "GET":
        form.assigned_to.data = task.assigned_to or 0
    if form.validate_on_submit():
        assignee_id = form.assigned_to.data or None
        allowed = {u.id for u in workspace.members}
        if assignee_id and assignee_id not in allowed:
            flash("Assignee must belong to this workspace.", "danger")
            return render_template("task_form.html", form=form, workspace=workspace, heading="Edit task")
        task.title = form.title.data.strip()
        task.description = (form.description.data or "").strip()
        task.assigned_to = assignee_id
        task.priority = form.priority.data
        task.status = form.status.data
        task.due_date = form.due_date.data
        db.session.commit()
        flash("Task updated.", "success")
        return redirect(url_for("workspace_detail", workspace_id=workspace.id))
    return render_template("task_form.html", form=form, workspace=workspace, heading="Edit task")

@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def task_delete(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        abort(404)
    workspace = get_workspace_or_404(task.workspace_id)
    if not (is_admin() or task.created_by == current_user.id or workspace.created_by == current_user.id):
        abort(403)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("workspace_detail", workspace_id=workspace.id))

@app.route("/workspaces/<int:workspace_id>/messages", methods=["POST"])
@login_required
def post_message(workspace_id):
    workspace = get_workspace_or_404(workspace_id)
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(workspace_id=workspace.id, user_id=current_user.id, body=form.body.data.strip())
        db.session.add(msg)
        db.session.commit()
        flash("Message posted.", "success")
    else:
        flash("Message must contain between 1 and 2000 characters.", "warning")
    return redirect(url_for("workspace_detail", workspace_id=workspace.id) + "#discussions")

def upload_to_storage(file_obj, object_key):
    bucket = current_app.config["S3_BUCKET"]
    if bucket:
        s3_client().upload_fileobj(
            file_obj, bucket, object_key,
            ExtraArgs={"ContentType": file_obj.mimetype or "application/octet-stream"}
        )
        return "s3"
    target = Path(current_app.config["UPLOAD_FOLDER"]) / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    file_obj.save(target)
    return "local"

@app.route("/workspaces/<int:workspace_id>/files/upload", methods=["POST"])
@login_required
def file_upload(workspace_id):
    workspace = get_workspace_or_404(workspace_id)
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        flash("Choose a file first.", "warning")
        return redirect(url_for("workspace_detail", workspace_id=workspace.id) + "#files")
    original_name = secure_filename(uploaded.filename)
    if not original_name:
        flash("Invalid filename.", "danger")
        return redirect(url_for("workspace_detail", workspace_id=workspace.id) + "#files")
    key = f"{workspace.id}/{uuid.uuid4().hex}_{original_name}"
    try:
        storage_type = upload_to_storage(uploaded, key)
        record = StoredFile(workspace_id=workspace.id, uploaded_by=current_user.id, original_name=original_name, storage_key=key, storage_type=storage_type)
        db.session.add(record)
        db.session.commit()
        flash("File uploaded.", "success")
    except (BotoCoreError, ClientError, OSError) as exc:
        db.session.rollback()
        current_app.logger.exception("File upload failed")
        flash("File upload failed. Check storage configuration and logs.", "danger")
    return redirect(url_for("workspace_detail", workspace_id=workspace.id) + "#files")

@app.route("/files/<int:file_id>/download")
@login_required
def file_download(file_id):
    record = db.session.get(StoredFile, file_id)
    if not record:
        abort(404)
    get_workspace_or_404(record.workspace_id)
    if record.storage_type == "s3":
        try:
            url = s3_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": current_app.config["S3_BUCKET"], "Key": record.storage_key},
                ExpiresIn=300
            )
            return redirect(url)
        except (BotoCoreError, ClientError):
            current_app.logger.exception("S3 download link failed")
            flash("Could not create download link.", "danger")
            return redirect(url_for("workspace_detail", workspace_id=record.workspace_id) + "#files")
    return send_from_directory(
        directory=str(Path(current_app.config["UPLOAD_FOLDER"]) / str(record.workspace_id)),
        path=Path(record.storage_key).name,
        as_attachment=True,
        download_name=record.original_name
    )

@app.route("/files/<int:file_id>/delete", methods=["POST"])
@login_required
def file_delete(file_id):
    record = db.session.get(StoredFile, file_id)
    if not record:
        abort(404)
    workspace = get_workspace_or_404(record.workspace_id)
    if not (is_admin() or record.uploaded_by == current_user.id or workspace.created_by == current_user.id):
        abort(403)
    try:
        if record.storage_type == "s3":
            s3_client().delete_object(Bucket=current_app.config["S3_BUCKET"], Key=record.storage_key)
        else:
            local_path = Path(app.config["UPLOAD_FOLDER"]) / record.storage_key
            if local_path.exists():
                local_path.unlink()
        db.session.delete(record)
        db.session.commit()
        flash("File deleted.", "info")
    except (BotoCoreError, ClientError, OSError):
        db.session.rollback()
        current_app.logger.exception("File deletion failed")
        flash("Could not delete file; check logs.", "danger")
    return redirect(url_for("workspace_detail", workspace_id=workspace.id) + "#files")

@app.route("/users")
@login_required
def users():
    admin_required()
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users.html", users=all_users)

@app.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
def update_role(user_id):
    admin_required()
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    form = RoleForm()
    form.role.choices = [("Member", "Member"), ("Admin", "Admin")]
    if form.validate_on_submit():
        if user.id == current_user.id and form.role.data != "Admin":
            flash("You cannot remove your own admin role.", "warning")
        else:
            user.role = form.role.data
            db.session.commit()
            flash("User role updated.", "success")
    else:
        flash("Invalid role update.", "danger")
    return redirect(url_for("users"))

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You do not have permission to access this resource."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The requested page was not found."), 404

@app.errorhandler(413)
def too_large(_):
    return render_template("error.html", code=413, message="The uploaded file exceeds the configured size limit."), 413

init_db()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=int(os.getenv("PORT", "5000")))

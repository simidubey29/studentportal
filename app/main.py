from datetime import datetime, date
from typing import Optional

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from passlib.context import CryptContext
from jose import JWTError, jwt

from .database import Base, engine, get_db
from .models import (
    User,
    Assignment,
    AssignmentStudent,
    Submission,
    Mark,
    Attendance,
    Notice,
    Timetable,
    Project,
    ProjectMember,
    Task,
)

from .schemas import (
    Login,
    StudentRegister,
    AssignmentCreate,
    AssignmentSubmit,
    GradeSubmission,
    MarkCreate,
    AttendanceCreate,
    NoticeCreate,
    ProjectCreate,
    TaskCreate,
    TaskStatus,
)


# ============================================================
# APP CONFIGURATION
# ============================================================

app = FastAPI(
    title="Student Academic Portal API",
    description="Role-based Student Academic Portal Backend",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# AUTHENTICATION CONFIGURATION
# ============================================================

pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

SECRET = "academic-portal-secret-change-this"

ALGORITHM = "HS256"

# This creates the 🔒 Authorize button in Swagger
security = HTTPBearer()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_token(user: User):
    payload = {
        "sub": str(user.id),
        "role": user.role,
    }

    token = jwt.encode(
        payload,
        SECRET,
        algorithm=ALGORITHM
    )

    return token


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=[ALGORITHM],
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def require_role(*allowed_roles):
    def role_checker(
        user: User = Depends(current_user)
    ):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )

        return user

    return role_checker


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "message": "Student Academic Portal backend is running",
    }


# ============================================================
# AUTH - LOGIN
# ============================================================

@app.post("/api/auth/login")
def login(
    data: Login,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not pwd.verify(
        data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = create_token(user)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "student_id": user.student_id,
            "department": user.department,
            "semester": user.semester,
        },
    }


# ============================================================
# STUDENT REGISTRATION
# ============================================================

@app.post("/api/auth/register")
def register_student(
    data: StudentRegister,
    db: Session = Depends(get_db),
):
    existing_email = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    existing_student = (
        db.query(User)
        .filter(User.student_id == data.student_id)
        .first()
    )

    if existing_student:
        raise HTTPException(
            status_code=400,
            detail="Student ID already registered",
        )

    user = User(
        name=data.name,
        email=data.email,
        password_hash=pwd.hash(data.password),
        role="student",
        student_id=data.student_id,
        department=data.department,
        semester=data.semester,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Student registered successfully",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "student_id": user.student_id,
        },
    }


# ============================================================
# ADMIN - ALL USERS
# ============================================================

@app.get("/api/admin/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_role("admin")
    ),
):
    users = (
        db.query(User)
        .order_by(User.id)
        .all()
    )

    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "student_id": user.student_id,
            "department": user.department,
            "semester": user.semester,
            "created_at": user.created_at,
        }
        for user in users
    ]


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/api/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role == "student":

        assignments_count = (
            db.query(AssignmentStudent)
            .filter(
                AssignmentStudent.student_id == user.id
            )
            .count()
        )

        submissions_count = (
            db.query(Submission)
            .filter(
                Submission.student_id == user.id,
                Submission.submitted_at.isnot(None),
            )
            .count()
        )

        return {
            "role": "student",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "student_id": user.student_id,
                "department": user.department,
                "semester": user.semester,
            },
            "assignments": assignments_count,
            "submissions": submissions_count,
        }

    elif user.role == "faculty":

        assignments_count = (
            db.query(Assignment)
            .filter(
                Assignment.faculty_id == user.id
            )
            .count()
        )

        return {
            "role": "faculty",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "department": user.department,
            },
            "assignments": assignments_count,
        }

    elif user.role == "admin":

        students_count = (
            db.query(User)
            .filter(User.role == "student")
            .count()
        )

        faculty_count = (
            db.query(User)
            .filter(User.role == "faculty")
            .count()
        )

        admin_count = (
            db.query(User)
            .filter(User.role == "admin")
            .count()
        )

        return {
            "role": "admin",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },
            "students": students_count,
            "faculty": faculty_count,
            "admins": admin_count,
        }

    raise HTTPException(
        status_code=400,
        detail="Unknown user role",
    )


# ============================================================
# ASSIGNMENTS - VIEW
# ============================================================

@app.get("/api/assignments")
def get_assignments(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role == "student":

        assignments = (
            db.query(Assignment)
            .join(
                AssignmentStudent,
                Assignment.id
                == AssignmentStudent.assignment_id,
            )
            .filter(
                AssignmentStudent.student_id == user.id
            )
            .order_by(Assignment.deadline)
            .all()
        )

    elif user.role == "faculty":

        assignments = (
            db.query(Assignment)
            .filter(
                Assignment.faculty_id == user.id
            )
            .order_by(Assignment.deadline)
            .all()
        )

    elif user.role == "admin":

        assignments = (
            db.query(Assignment)
            .order_by(Assignment.deadline)
            .all()
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    result = []

    for assignment in assignments:

        item = {
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "subject": assignment.subject,
            "deadline": assignment.deadline,
            "faculty_id": assignment.faculty_id,
            "max_marks": assignment.max_marks,
            "created_at": assignment.created_at,
        }

        if user.role == "student":

            submission = (
                db.query(Submission)
                .filter(
                    Submission.assignment_id
                    == assignment.id,
                    Submission.student_id
                    == user.id,
                )
                .first()
            )

            if submission:

                item["submission"] = {
                    "id": submission.id,
                    "submitted_at": submission.submitted_at,
                    "status": submission.status,
                    "marks": submission.marks,
                    "feedback": submission.feedback,
                }

            else:

                item["submission"] = {
                    "id": None,
                    "submitted_at": None,
                    "status": "Not Submitted",
                    "marks": None,
                    "feedback": None,
                }

        result.append(item)

    return result


# ============================================================
# ASSIGNMENT - CREATE
# ============================================================

@app.post("/api/assignments")
def create_assignment(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    faculty: User = Depends(
        require_role("faculty", "admin")
    ),
):
    assignment = Assignment(
        title=data.title,
        description=data.description,
        subject=data.subject,
        deadline=data.deadline,
        faculty_id=faculty.id,
        max_marks=data.max_marks,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    # Assign to selected students
    for student_id in data.student_ids:

        student = (
            db.query(User)
            .filter(
                User.id == student_id,
                User.role == "student",
            )
            .first()
        )

        if not student:
            continue

        assignment_student = AssignmentStudent(
            assignment_id=assignment.id,
            student_id=student_id,
        )

        db.add(assignment_student)

        # Create initial submission record
        submission = Submission(
            assignment_id=assignment.id,
            student_id=student_id,
            submission_text=None,
            submitted_at=None,
            status="Not Submitted",
        )

        db.add(submission)

    db.commit()

    return {
        "message": "Assignment created successfully",
        "assignment_id": assignment.id,
    }


# ============================================================
# ASSIGNMENT - STUDENT SUBMISSION
# ============================================================

@app.post(
    "/api/assignments/{assignment_id}/submit"
)
def submit_assignment(
    assignment_id: int,
    data: AssignmentSubmit,
    db: Session = Depends(get_db),
    student: User = Depends(
        require_role("student")
    ),
):
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id
        )
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found",
        )

    assigned = (
        db.query(AssignmentStudent)
        .filter(
            AssignmentStudent.assignment_id
            == assignment_id,
            AssignmentStudent.student_id
            == student.id,
        )
        .first()
    )

    if not assigned:
        raise HTTPException(
            status_code=403,
            detail="This assignment is not assigned to you",
        )

    submission = (
        db.query(Submission)
        .filter(
            Submission.assignment_id
            == assignment_id,
            Submission.student_id
            == student.id,
        )
        .first()
    )

    if not submission:

        submission = Submission(
            assignment_id=assignment_id,
            student_id=student.id,
        )

        db.add(submission)

    submission.submission_text = data.submission_text

    # Exact server-side submission time
    submission.submitted_at = datetime.utcnow()

    if submission.submitted_at > assignment.deadline:
        submission.status = "Late"
    else:
        submission.status = "Submitted"

    db.commit()
    db.refresh(submission)

    return {
        "message": "Assignment submitted successfully",
        "submission_id": submission.id,
        "submitted_at": submission.submitted_at,
        "status": submission.status,
    }


# ============================================================
# FACULTY - VIEW SUBMISSIONS
# ============================================================

@app.get(
    "/api/assignments/{assignment_id}/submissions"
)
def get_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    faculty: User = Depends(
        require_role("faculty", "admin")
    ),
):
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id
        )
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found",
        )

    if (
        faculty.role == "faculty"
        and assignment.faculty_id != faculty.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not own this assignment",
        )

    submissions = (
        db.query(Submission)
        .filter(
            Submission.assignment_id
            == assignment_id
        )
        .all()
    )

    result = []

    for submission in submissions:

        student = (
            db.query(User)
            .filter(
                User.id == submission.student_id
            )
            .first()
        )

        result.append({
            "submission_id": submission.id,
            "student_id": submission.student_id,
            "student_name": (
                student.name if student else None
            ),
            "student_email": (
                student.email if student else None
            ),
            "submission_text": submission.submission_text,
            "submitted_at": submission.submitted_at,
            "status": submission.status,
            "marks": submission.marks,
            "feedback": submission.feedback,
        })

    return result


# ============================================================
# FACULTY - GRADE SUBMISSION
# ============================================================

@app.put(
    "/api/submissions/{submission_id}/grade"
)
def grade_submission(
    submission_id: int,
    data: GradeSubmission,
    db: Session = Depends(get_db),
    faculty: User = Depends(
        require_role("faculty", "admin")
    ),
):
    submission = (
        db.query(Submission)
        .filter(
            Submission.id == submission_id
        )
        .first()
    )

    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Submission not found",
        )

    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id
            == submission.assignment_id
        )
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found",
        )

    if (
        faculty.role == "faculty"
        and assignment.faculty_id != faculty.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot grade this assignment",
        )

    if data.marks < 0:
        raise HTTPException(
            status_code=400,
            detail="Marks cannot be negative",
        )

    if data.marks > assignment.max_marks:
        raise HTTPException(
            status_code=400,
            detail="Marks cannot exceed maximum marks",
        )

    submission.marks = data.marks
    submission.feedback = data.feedback

    db.commit()
    db.refresh(submission)

    return {
        "message": "Submission graded successfully",
        "submission_id": submission.id,
        "marks": submission.marks,
        "feedback": submission.feedback,
    }


# ============================================================
# MARKS - STUDENT VIEW
# ============================================================

@app.get("/api/marks")
def get_marks(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role == "student":

        marks = (
            db.query(Mark)
            .filter(
                Mark.student_id == user.id
            )
            .order_by(Mark.created_at.desc())
            .all()
        )

    elif user.role in ["faculty", "admin"]:

        marks = (
            db.query(Mark)
            .order_by(Mark.created_at.desc())
            .all()
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    return [
        {
            "id": mark.id,
            "student_id": mark.student_id,
            "subject": mark.subject,
            "exam": mark.exam,
            "marks": mark.marks,
            "max_marks": mark.max_marks,
            "created_at": mark.created_at,
        }
        for mark in marks
    ]


# ============================================================
# MARKS - CREATE
# ============================================================

@app.post("/api/marks")
def create_mark(
    data: MarkCreate,
    db: Session = Depends(get_db),
    faculty: User = Depends(
        require_role("faculty", "admin")
    ),
):
    student = (
        db.query(User)
        .filter(
            User.id == data.student_id,
            User.role == "student",
        )
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    if data.marks < 0:
        raise HTTPException(
            status_code=400,
            detail="Marks cannot be negative",
        )

    if data.marks > data.max_marks:
        raise HTTPException(
            status_code=400,
            detail="Marks cannot exceed maximum marks",
        )

    mark = Mark(
        student_id=data.student_id,
        subject=data.subject,
        exam=data.exam,
        marks=data.marks,
        max_marks=data.max_marks,
    )

    db.add(mark)
    db.commit()
    db.refresh(mark)

    return {
        "message": "Marks added successfully",
        "mark_id": mark.id,
    }


# ============================================================
# ATTENDANCE - VIEW
# ============================================================

@app.get("/api/attendance")
def get_attendance(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role == "student":

        attendance = (
            db.query(Attendance)
            .filter(
                Attendance.student_id == user.id
            )
            .order_by(
                Attendance.attendance_date.desc()
            )
            .all()
        )

    elif user.role in ["faculty", "admin"]:

        attendance = (
            db.query(Attendance)
            .order_by(
                Attendance.attendance_date.desc()
            )
            .all()
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    return [
        {
            "id": item.id,
            "student_id": item.student_id,
            "subject": item.subject,
            "attendance_date": item.attendance_date,
            "status": item.status,
        }
        for item in attendance
    ]


# ============================================================
# ATTENDANCE - CREATE
# ============================================================

@app.post("/api/attendance")
def create_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    faculty: User = Depends(
        require_role("faculty", "admin")
    ),
):
    student = (
        db.query(User)
        .filter(
            User.id == data.student_id,
            User.role == "student",
        )
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    if data.status not in ["Present", "Absent"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be Present or Absent",
        )

    try:
        attendance_date = date.fromisoformat(
            data.attendance_date
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="attendance_date must be YYYY-MM-DD",
        )

    attendance = Attendance(
        student_id=data.student_id,
        subject=data.subject,
        attendance_date=attendance_date,
        status=data.status,
    )

    db.add(attendance)
    db.commit()
    db.refresh(attendance)

    return {
        "message": "Attendance recorded successfully",
        "attendance_id": attendance.id,
    }


# ============================================================
# NOTICES - VIEW
# ============================================================

@app.get("/api/notices")
def get_notices(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    notices = (
        db.query(Notice)
        .order_by(Notice.created_at.desc())
        .all()
    )

    return [
        {
            "id": notice.id,
            "title": notice.title,
            "message": notice.message,
            "created_by": notice.created_by,
            "created_at": notice.created_at,
        }
        for notice in notices
    ]


# ============================================================
# NOTICES - CREATE
# ============================================================

@app.post("/api/notices")
def create_notice(
    data: NoticeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_role("faculty", "admin")
    ),
):
    notice = Notice(
        title=data.title,
        message=data.message,
        created_by=user.id,
    )

    db.add(notice)
    db.commit()
    db.refresh(notice)

    return {
        "message": "Notice created successfully",
        "notice_id": notice.id,
    }


# ============================================================
# TIMETABLE - VIEW
# ============================================================

@app.get("/api/timetable")
def get_timetable(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    timetable = (
        db.query(Timetable)
        .order_by(Timetable.id)
        .all()
    )

    return [
        {
            "id": item.id,
            "day": item.day,
            "time": item.time,
            "subject": item.subject,
            "faculty": item.faculty,
            "room": item.room,
        }
        for item in timetable
    ]


# ============================================================
# PROJECTS - VIEW
# ============================================================

@app.get("/api/projects")
def get_projects(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role == "student":

        projects = (
            db.query(Project)
            .join(
                ProjectMember,
                Project.id
                == ProjectMember.project_id,
            )
            .filter(
                ProjectMember.user_id == user.id
            )
            .all()
        )

    elif user.role in ["faculty", "admin"]:

        projects = (
            db.query(Project)
            .order_by(Project.id.desc())
            .all()
        )

    else:
        projects = []

    return [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "deadline": project.deadline,
            "status": project.status,
            "owner_id": project.owner_id,
        }
        for project in projects
    ]


# ============================================================
# PROJECTS - CREATE
# ============================================================

@app.post("/api/projects")
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_role("student", "faculty", "admin")
    ),
):
    project = Project(
        name=data.name,
        description=data.description,
        deadline=data.deadline,
        owner_id=user.id,
        status="Planning",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Add owner as project member
    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
    )

    db.add(member)
    db.commit()

    return {
        "message": "Project created successfully",
        "project_id": project.id,
    }


# ============================================================
# TASKS - CREATE
# ============================================================

@app.post("/api/tasks")
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_role("student", "faculty", "admin")
    ),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == data.project_id
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    task = Task(
        project_id=data.project_id,
        title=data.title,
        assigned_to=data.assigned_to,
        deadline=data.deadline,
        status="Pending",
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "message": "Task created successfully",
        "task_id": task.id,
    }


# ============================================================
# TASKS - UPDATE STATUS
# ============================================================

@app.patch("/api/tasks/{task_id}")
def update_task(
    task_id: int,
    data: TaskStatus,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_role("student", "faculty", "admin")
    ),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    allowed_statuses = [
        "Pending",
        "In Progress",
        "Completed",
    ]

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Status must be one of: "
                + ", ".join(allowed_statuses)
            ),
        )

    task.status = data.status

    db.commit()
    db.refresh(task)

    return {
        "message": "Task updated successfully",
        "task_id": task.id,
        "status": task.status,
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Student Academic Portal API",
        "docs": "/docs",
        "health": "/api/health",
    }
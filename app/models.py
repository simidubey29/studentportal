from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Float,
    ForeignKey,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship

from .database import Base


# =========================================================
# USER
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    email = Column(String(150), unique=True, nullable=False, index=True)

    password_hash = Column(String(255), nullable=False)

    role = Column(
        Enum("student", "faculty", "admin"),
        nullable=False
    )

    student_id = Column(String(50), unique=True, nullable=True)

    department = Column(String(100), nullable=True)

    semester = Column(String(20), nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# =========================================================
# ASSIGNMENT
# =========================================================

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(200), nullable=False)

    description = Column(Text, nullable=True)

    subject = Column(String(150), nullable=False)

    deadline = Column(DateTime, nullable=False)

    faculty_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    max_marks = Column(Float, default=100)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    faculty = relationship(
        "User",
        foreign_keys=[faculty_id]
    )

    students = relationship(
        "AssignmentStudent",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )

    submissions = relationship(
        "Submission",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )


# =========================================================
# ASSIGNMENT STUDENTS
# =========================================================

class AssignmentStudent(Base):
    __tablename__ = "assignment_students"

    id = Column(Integer, primary_key=True, index=True)

    assignment_id = Column(
        Integer,
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False
    )

    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    assignment = relationship(
        "Assignment",
        back_populates="students"
    )

    student = relationship(
        "User"
    )


# =========================================================
# SUBMISSION
# =========================================================

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)

    assignment_id = Column(
        Integer,
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False
    )

    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    submission_text = Column(
        Text,
        nullable=True
    )

    submitted_at = Column(
        DateTime,
        nullable=True
    )

    status = Column(
        Enum(
            "Not Submitted",
            "Submitted",
            "Late"
        ),
        default="Not Submitted"
    )

    marks = Column(
        Float,
        nullable=True
    )

    feedback = Column(
        Text,
        nullable=True
    )

    assignment = relationship(
        "Assignment",
        back_populates="submissions"
    )

    student = relationship(
        "User"
    )


# =========================================================
# MARKS
# =========================================================

class Mark(Base):
    __tablename__ = "marks"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    subject = Column(
        String(150),
        nullable=False
    )

    exam = Column(
        String(150),
        nullable=False
    )

    marks = Column(
        Float,
        nullable=False
    )

    max_marks = Column(
        Float,
        default=100
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    student = relationship("User")


# =========================================================
# ATTENDANCE
# =========================================================

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    subject = Column(
        String(150),
        nullable=False
    )

    attendance_date = Column(
        Date,
        nullable=False
    )

    status = Column(
        Enum("Present", "Absent"),
        default="Present"
    )

    student = relationship("User")


# =========================================================
# NOTICES
# =========================================================

class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(
        String(200),
        nullable=False
    )

    message = Column(
        Text,
        nullable=False
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    creator = relationship("User")


# =========================================================
# TIMETABLE
# =========================================================

class Timetable(Base):
    __tablename__ = "timetable"

    id = Column(Integer, primary_key=True, index=True)

    day = Column(
        String(20),
        nullable=False
    )

    time = Column(
        String(50),
        nullable=False
    )

    subject = Column(
        String(150),
        nullable=False
    )

    faculty = Column(
        String(150),
        nullable=True
    )

    room = Column(
        String(100),
        nullable=True
    )


# =========================================================
# PROJECT
# =========================================================

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String(200),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    deadline = Column(
        DateTime,
        nullable=True
    )

    status = Column(
        String(50),
        default="Planning"
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    owner = relationship("User")


# =========================================================
# PROJECT MEMBERS
# =========================================================

class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )


# =========================================================
# TASKS
# =========================================================

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )

    title = Column(
        String(200),
        nullable=False
    )

    assigned_to = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    deadline = Column(
        DateTime,
        nullable=True
    )

    status = Column(
        String(50),
        default="Pending"
    )
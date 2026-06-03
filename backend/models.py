from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base
import datetime

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String)
    job_url = Column(String, unique=True, index=True)
    description = Column(Text)
    date_posted = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    application_status = Column(String, default="Not Applied")
    application_notes = Column(Text, default="")
    is_updated = Column(Boolean, default=False)

    analysis = relationship("JobAnalysis", back_populates="job", uselist=False)
    application = relationship("Application", back_populates="job", uselist=False)
    versions = relationship("JobVersion", back_populates="job", order_by="desc(JobVersion.changed_at)")

class JobVersion(Base):
    __tablename__ = "job_versions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    old_title = Column(String)
    old_description = Column(Text)
    changed_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    job = relationship("Job", back_populates="versions")

class JobAnalysis(Base):
    __tablename__ = "job_analysis"

    job_id = Column(Integer, ForeignKey("jobs.id"), primary_key=True)
    role_family = Column(String)
    seniority_level = Column(String)
    experience_requirement = Column(Integer)
    fit_score = Column(Float)
    decision = Column(String) # KEEP/REVIEW/REJECT
    score_breakdown = Column(Text)
    evidence = Column(Text)

    job = relationship("Job", back_populates="analysis")

class Application(Base):
    __tablename__ = "applications"

    job_id = Column(Integer, ForeignKey("jobs.id"), primary_key=True)
    status = Column(String)
    applied_via = Column(String)
    cv_version = Column(String)

    job = relationship("Job", back_populates="application")

from fastapi import APIRouter

from app.api.v1.endpoints import (
    applications,
    auth,
    companies,
    interview_prep,
    jobs,
    resume_intelligence,
    resumes,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(resumes.router)
api_router.include_router(resume_intelligence.router)
api_router.include_router(interview_prep.router)
api_router.include_router(companies.router)

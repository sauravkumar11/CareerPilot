import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession, require_owner
from app.core.config import get_settings
from app.core.rate_limit import RateLimitExceeded, check_rate_limit
from app.domain.models.resume import DocumentFormat, DocumentType, ParseStatus
from app.domain.schemas.resume import (
    CoverLetterRequest,
    DocumentExportRequest,
    DocumentRead,
    ResumeAnalysisRead,
    ResumeAnalyzeRequest,
    ResumeContent,
    ResumeCustomizeRequest,
    ResumeRead,
    ResumeUploadResponse,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.services.cover_letter_service import CoverLetterGenerationError, CoverLetterService
from app.services.document_export_service import DocumentExportService
from app.services.fabrication_guard import FabricationDetectedError
from app.services.resume_analysis_service import ResumeAnalysisError, ResumeAnalysisService
from app.services.resume_customization_service import ResumeCustomizationError, ResumeCustomizationService
from app.services.resume_parser_service import ResumeParserService, ResumeParsingError
from app.services.storage_service import generate_storage_key, get_storage

router = APIRouter(tags=["resume-intelligence"])


def _handle_rate_limit(exc: RateLimitExceeded):
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Rate limit exceeded. Try again in {exc.retry_after_seconds} seconds.",
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


@router.post("/resumes/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    label: str = "Uploaded resume",
):
    settings = get_settings()

    if file.content_type not in settings.ALLOWED_RESUME_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_RESUME_MIME_TYPES)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max upload size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB",
        )
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    extension = "pdf" if file.content_type == "application/pdf" else "docx"
    storage = get_storage()
    key = generate_storage_key(current_user.id, "resumes", extension)
    stored_path = await storage.save(key, file_bytes)

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.create(
        user_id=current_user.id,
        label=label,
        content={},
        is_primary=False,
        version=1,
        parent_resume_id=None,
        source_file_path=stored_path,
        parse_status=ParseStatus.PENDING,
    )
    await resume_repo.commit()

    parser = ResumeParserService()
    try:
        content = await parser.parse(file_bytes, file.content_type)
        resume.content = content.model_dump()
        resume.parse_status = ParseStatus.PARSED
    except ResumeParsingError as exc:
        resume.parse_status = ParseStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    await db.commit()
    return ResumeUploadResponse(id=resume.id, parse_status=resume.parse_status)


@router.get("/resumes/{resume_id}", response_model=ResumeRead)
async def get_resume(resume_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    repo = ResumeRepository(db)
    resume = await repo.get(resume_id)
    require_owner(resume, current_user, not_found_detail="Resume not found")
    return resume


@router.get("/resumes/{resume_id}/versions", response_model=list[ResumeRead])
async def list_resume_versions(resume_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    repo = ResumeRepository(db)
    root = await repo.get(resume_id)
    require_owner(root, current_user, not_found_detail="Resume not found")

    # Walk up to the true root if this id is itself a derived version.
    lineage_root_id = root.parent_resume_id or root.id
    return await repo.list_lineage(lineage_root_id, current_user.id)


@router.post("/resumes/{resume_id}/analyze", response_model=ResumeAnalysisRead)
async def analyze_resume(
    resume_id: uuid.UUID,
    payload: ResumeAnalyzeRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    try:
        await check_rate_limit(current_user.id, "resume_analysis")
    except RateLimitExceeded as exc:
        _handle_rate_limit(exc)

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get(resume_id)
    require_owner(resume, current_user, not_found_detail="Resume not found")

    if resume.parse_status != ParseStatus.PARSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resume is not ready for analysis (status: {resume.parse_status.value})",
        )

    target_job = None
    if payload.target_job_id:
        job_repo = JobRepository(db)
        target_job = await job_repo.get_with_company(payload.target_job_id)
        if not target_job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target job not found")

    content = ResumeContent.model_validate(resume.content)
    service = ResumeAnalysisService()
    try:
        result = await service.analyze(content, target_job=target_job)
    except ResumeAnalysisError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    from app.domain.models.resume import ResumeAnalysis

    analysis = ResumeAnalysis(
        resume_id=resume.id,
        target_job_id=target_job.id if target_job else None,
        ats_score=result["ats_score"],
        extracted_skills=result["extracted_skills"],
        missing_skills_by_role=result.get("missing_skills_by_role"),
        strengths=result["strengths"],
        weaknesses=result["weaknesses"],
    )
    await resume_repo.add_analysis(analysis)
    await db.commit()
    return analysis


@router.get("/resumes/{resume_id}/analysis", response_model=ResumeAnalysisRead)
async def get_latest_analysis(resume_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get(resume_id)
    require_owner(resume, current_user, not_found_detail="Resume not found")

    analysis = await resume_repo.latest_analysis(resume_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analysis yet for this resume")
    return analysis


@router.post("/resumes/{resume_id}/customize", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def customize_resume(
    resume_id: uuid.UUID,
    payload: ResumeCustomizeRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    try:
        await check_rate_limit(current_user.id, "resume_customization")
    except RateLimitExceeded as exc:
        _handle_rate_limit(exc)

    resume_repo = ResumeRepository(db)
    source_resume = await resume_repo.get(resume_id)
    require_owner(source_resume, current_user, not_found_detail="Resume not found")

    if source_resume.parse_status != ParseStatus.PARSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resume is not ready for customization (status: {source_resume.parse_status.value})",
        )

    job_repo = JobRepository(db)
    target_job = await job_repo.get_with_company(payload.job_id)
    if not target_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target job not found")

    source_content = ResumeContent.model_validate(source_resume.content)
    service = ResumeCustomizationService()
    try:
        customized_content = await service.customize(source_content, target_job)
    except ResumeCustomizationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    lineage_root_id = source_resume.parent_resume_id or source_resume.id
    existing_versions = await resume_repo.list_lineage(lineage_root_id, current_user.id)
    next_version = max((r.version for r in existing_versions), default=source_resume.version) + 1

    new_resume = await resume_repo.create(
        user_id=current_user.id,
        label=payload.label or f"{source_resume.label} (tailored — {target_job.title})",
        content=customized_content.model_dump(),
        is_primary=False,
        version=next_version,
        parent_resume_id=lineage_root_id,
        source_file_path=None,
        parse_status=ParseStatus.PARSED,
    )
    await resume_repo.commit()
    return new_resume


@router.post("/resumes/{resume_id}/export", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def export_resume(
    resume_id: uuid.UUID,
    payload: DocumentExportRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get(resume_id)
    require_owner(resume, current_user, not_found_detail="Resume not found")

    if resume.parse_status != ParseStatus.PARSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resume is not ready for export (status: {resume.parse_status.value})",
        )

    content = ResumeContent.model_validate(resume.content)

    if payload.document_format == DocumentFormat.PDF:
        file_bytes = DocumentExportService.resume_to_pdf(content)
        extension = "pdf"
    else:
        file_bytes = DocumentExportService.resume_to_docx(content)
        extension = "docx"

    storage = get_storage()
    key = generate_storage_key(current_user.id, "documents", extension)
    stored_path = await storage.save(key, file_bytes)

    document_repo = DocumentRepository(db)
    document = await document_repo.create(
        user_id=current_user.id,
        source_resume_id=resume.id,
        job_id=None,
        document_type=DocumentType.TAILORED_RESUME,
        document_format=payload.document_format,
        storage_path=stored_path,
        generation_prompt_summary=None,
    )
    await document_repo.commit()
    return document


@router.post(
    "/applications/{application_id}/cover-letter", response_model=DocumentRead, status_code=status.HTTP_201_CREATED
)
async def generate_cover_letter(
    application_id: uuid.UUID,
    payload: CoverLetterRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    try:
        await check_rate_limit(current_user.id, "cover_letter")
    except RateLimitExceeded as exc:
        _handle_rate_limit(exc)

    application_repo = ApplicationRepository(db)
    application = await application_repo.get_for_user(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    resume_repo = ResumeRepository(db)
    if payload.resume_id:
        resume = await resume_repo.get(payload.resume_id)
        require_owner(resume, current_user, not_found_detail="Resume not found")
    else:
        resume = await resume_repo.get_primary(current_user.id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No primary resume set — specify resume_id or mark a resume as primary",
            )

    if resume.parse_status != ParseStatus.PARSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resume is not ready (status: {resume.parse_status.value})",
        )

    content = ResumeContent.model_validate(resume.content)
    service = CoverLetterService()
    try:
        letter_text = await service.generate(content, application.job, tone=payload.tone)
    except (CoverLetterGenerationError, FabricationDetectedError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    file_bytes = DocumentExportService.cover_letter_to_pdf(letter_text)
    storage = get_storage()
    key = generate_storage_key(current_user.id, "documents", "pdf")
    stored_path = await storage.save(key, file_bytes)

    document_repo = DocumentRepository(db)
    document = await document_repo.create(
        user_id=current_user.id,
        source_resume_id=resume.id,
        job_id=application.job_id,
        document_type=DocumentType.COVER_LETTER,
        document_format=DocumentFormat.PDF,
        storage_path=stored_path,
        generation_prompt_summary=f"tone={payload.tone}",
    )
    await document_repo.commit()

    application.cover_letter_document_id = document.id
    await db.commit()

    return document


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(document_id: uuid.UUID, db: DbSession, current_user: CurrentUser):
    repo = DocumentRepository(db)
    document = await repo.get(document_id)
    require_owner(document, current_user, not_found_detail="Document not found")
    return document

import pytest

from app.domain.schemas.resume import (
    ResumeContact,
    ResumeContent,
    ResumeExperienceEntry,
    ResumeProjectEntry,
)
from app.services.fabrication_guard import FabricationDetectedError, check_for_fabrication


@pytest.fixture
def sample_resume() -> ResumeContent:
    return ResumeContent(
        contact=ResumeContact(full_name="Jane Doe", email="jane@example.com"),
        summary="Backend engineer focused on distributed systems.",
        skills=["Python", "PostgreSQL", "Kubernetes"],
        experience=[
            ResumeExperienceEntry(
                company="Acme Corp",
                title="Senior Backend Engineer",
                start_date="Jan 2022",
                end_date="Present",
                bullets=["Built a payments processing pipeline handling 10k transactions/sec"],
            )
        ],
        projects=[
            ResumeProjectEntry(
                name="OpenTracker",
                bullets=["Open-source issue tracker used by 200+ repos"],
                tech_stack=["Django", "React"],
            )
        ],
        achievements=["Speaker at PyCon 2023"],
    )


def test_restating_source_content_does_not_trigger_fabrication(sample_resume):
    generated = (
        "Jane Doe is a Senior Backend Engineer with experience at Acme Corp, "
        "skilled in Python, PostgreSQL, and Kubernetes, and built OpenTracker using Django and React."
    )
    check_for_fabrication(sample_resume, generated)  # should not raise


def test_new_company_name_triggers_fabrication(sample_resume):
    generated = "Jane previously worked as a Senior Backend Engineer at Globodyne Corporation."
    with pytest.raises(FabricationDetectedError) as exc_info:
        check_for_fabrication(sample_resume, generated)
    assert any("globodyne" in term.lower() for term in exc_info.value.suspect_terms)


def test_new_skill_triggers_fabrication(sample_resume):
    generated = "Jane is an expert in Rust and WebAssembly, technologies not on her resume."
    with pytest.raises(FabricationDetectedError):
        check_for_fabrication(sample_resume, generated)


def test_extra_allowed_terms_permits_target_company_and_role(sample_resume):
    generated = "I'm excited to apply for the Staff Engineer role at Novacorp."
    with pytest.raises(FabricationDetectedError):
        check_for_fabrication(sample_resume, generated)

    check_for_fabrication(
        sample_resume, generated, extra_allowed_terms={"novacorp", "staff", "engineer", "role"}
    )


def test_lowercase_prose_never_flagged(sample_resume):
    generated = "jane is a strong communicator who collaborates well across teams and mentors junior engineers."
    check_for_fabrication(sample_resume, generated)  # should not raise — no capitalized proper nouns

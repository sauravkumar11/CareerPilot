import uuid

import pytest

from app.services.storage_service import LocalFileStorage, generate_storage_key


@pytest.fixture
def storage(tmp_path):
    return LocalFileStorage(root=str(tmp_path))


@pytest.mark.asyncio
async def test_save_and_read_roundtrip(storage):
    key = "users/abc/resumes/test.pdf"
    path = await storage.save(key, b"hello world")
    assert (await storage.read(path)) == b"hello world"


@pytest.mark.asyncio
async def test_save_creates_nested_directories(storage, tmp_path):
    key = "users/abc/documents/nested/deep/file.docx"
    await storage.save(key, b"content")
    assert (tmp_path / "users/abc/documents/nested/deep/file.docx").exists()


@pytest.mark.asyncio
async def test_read_missing_file_raises(storage):
    with pytest.raises(FileNotFoundError):
        await storage.read("/nonexistent/path/file.pdf")


@pytest.mark.asyncio
async def test_delete_removes_file(storage):
    path = await storage.save("users/x/resumes/a.pdf", b"data")
    await storage.delete(path)
    with pytest.raises(FileNotFoundError):
        await storage.read(path)


@pytest.mark.asyncio
async def test_path_traversal_rejected(storage):
    with pytest.raises(ValueError):
        await storage.save("../../../etc/passwd", b"malicious")


def test_generate_storage_key_is_scoped_per_user():
    user_id = uuid.uuid4()
    key = generate_storage_key(user_id, "resumes", "pdf")
    assert str(user_id) in key
    assert key.endswith(".pdf")
    assert "resumes" in key

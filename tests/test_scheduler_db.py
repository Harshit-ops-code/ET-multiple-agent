import os
import tempfile
import pytest

from job_store import JobStore

@pytest.fixture
def temp_job_store():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    store = JobStore(db_path=path)
    yield store
    os.remove(path)

def test_scheduled_posts(temp_job_store):
    store = temp_job_store
    
    # Check empty
    posts = store.get_scheduled_posts()
    assert len(posts) == 0
    
    # Add post
    store.add_scheduled_post("job-123", "instagram", "Now", "Test note", "Test title", "sent")
    
    # Check again
    posts = store.get_scheduled_posts()
    assert len(posts) == 1
    assert posts[0]["job_id"] == "job-123"
    assert posts[0]["platform"] == "instagram"
    assert posts[0]["status"] == "sent"
    
    # Update status
    store.update_scheduled_post_status("job-123", "instagram", "error")
    
    # Check updated
    posts = store.get_scheduled_posts()
    assert len(posts) == 1
    assert posts[0]["status"] == "error"

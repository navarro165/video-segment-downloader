import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import MagicMock
import json

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def mock_m3u8_content():
    """Mock m3u8 playlist content."""
    return """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
segment1.ts
#EXTINF:10.0,
segment2.ts
#EXTINF:10.0,
segment3.ts
#EXT-X-ENDLIST"""

@pytest.fixture
def mock_segment_content():
    """Mock video segment content."""
    return b"fake video segment content"

@pytest.fixture
def mock_curl_command():
    """Mock curl command for testing."""
    return """curl 'https://example.com/video/seg-1-v1-a1.ts' -H 'User-Agent: test' -H 'Accept: */*'"""

@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model for testing."""
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "This is a test transcription"}
    return mock_model

@pytest.fixture
def mock_requests_get(mocker, mock_m3u8_content, mock_segment_content):
    """Mock requests.get for testing."""
    mock_response = MagicMock()
    mock_response.text = mock_m3u8_content
    mock_response.content = mock_segment_content
    mock_response.raise_for_status = MagicMock()
    return mocker.patch('requests.get', return_value=mock_response)

@pytest.fixture
def mock_subprocess_run(mocker):
    """Mock subprocess.run for testing ffmpeg calls."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    return mocker.patch('subprocess.run', return_value=mock_process)

@pytest.fixture
def mock_whisper_load_model(mocker, mock_whisper_model):
    """Mock whisper.load_model for testing."""
    return mocker.patch('whisper.load_model', return_value=mock_whisper_model)

@pytest.fixture
def mock_tempfile(mocker, temp_dir):
    """Mock tempfile.mkdtemp for testing."""
    return mocker.patch('tempfile.mkdtemp', return_value=str(temp_dir))

@pytest.fixture
def mock_path_exists(mocker):
    """Mock Path.exists for testing."""
    return mocker.patch('pathlib.Path.exists', return_value=True)

@pytest.fixture
def mock_path_mkdir(mocker):
    """Mock Path.mkdir for testing."""
    return mocker.patch('pathlib.Path.mkdir')

@pytest.fixture
def mock_shutil_rmtree(mocker):
    """Mock shutil.rmtree for testing."""
    return mocker.patch('shutil.rmtree')

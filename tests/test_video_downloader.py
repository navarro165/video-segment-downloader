import pytest
from pathlib import Path
from video_downloader import VideoSegmentDownloader
import requests
import shlex

def test_sanitize_filename():
    """Test filename sanitization."""
    downloader = VideoSegmentDownloader()
    
    # Test basic sanitization
    assert downloader.sanitize_filename("test.mp4") == "test.mp4"
    assert downloader.sanitize_filename("test video.mp4") == "test_video.mp4"
    assert downloader.sanitize_filename("test/video.mp4") == "test_video.mp4"
    assert downloader.sanitize_filename("test\\video.mp4") == "test_video.mp4"
    assert downloader.sanitize_filename("test:video.mp4") == "test_video.mp4"
    
    # Test empty filename
    assert downloader.sanitize_filename("") == "video"

def test_validate_url():
    """Test URL validation."""
    downloader = VideoSegmentDownloader()
    
    # Test valid URLs
    assert downloader.validate_url("https://example.com/video.m3u8")
    assert downloader.validate_url("http://example.com/video.m3u8")
    
    # Test invalid URLs
    assert not downloader.validate_url("not-a-url")
    assert not downloader.validate_url("ftp://example.com")
    assert not downloader.validate_url("")

def test_parse_curl_command(mock_curl_command):
    """Test curl command parsing."""
    downloader = VideoSegmentDownloader()
    result = downloader.parse_curl_command(mock_curl_command)
    
    assert result['url'] == "https://example.com/video/seg-1-v1-a1.ts"
    assert result['headers']['User-Agent'] == "test"
    assert result['headers']['Accept'] == "*/*"

def test_get_segment_urls(mock_requests_get, mock_m3u8_content):
    """Test getting segment URLs from m3u8 playlist."""
    downloader = VideoSegmentDownloader()
    segments = downloader.get_segment_urls("https://example.com/video.m3u8")
    
    assert len(segments) == 3
    assert segments[0] == "segment1.ts"
    assert segments[1] == "segment2.ts"
    assert segments[2] == "segment3.ts"

def test_download_segments(mock_requests_get, mock_segment_content, temp_dir):
    """Test downloading video segments."""
    downloader = VideoSegmentDownloader()
    segments = ["segment1.ts", "segment2.ts", "segment3.ts"]
    base_url = "https://example.com/video"
    
    segments_dir = downloader.download_segments(segments, base_url, "test_video")
    assert segments_dir is not None
    
    # Verify segments were downloaded
    segment_files = list(Path(segments_dir).glob("segment_*.ts"))
    assert len(segment_files) == 3

def test_combine_segments(mock_subprocess_run, temp_dir):
    """Test combining video segments."""
    downloader = VideoSegmentDownloader()
    
    # Create mock segment files
    segments_dir = Path(temp_dir)
    for i in range(3):
        (segments_dir / f"segment_{i:03d}.ts").write_bytes(b"fake content")
    
    # Create file list
    file_list = segments_dir / "file_list.txt"
    with open(file_list, "w") as f:
        for i in range(3):
            f.write(f"file '{segments_dir}/segment_{i:03d}.ts'\n")
    
    output_file = downloader.combine_segments(segments_dir, "test_video.mp4")
    assert output_file is not None
    assert output_file.name == "test_video.mp4"

def test_cleanup(mock_shutil_rmtree, temp_dir):
    """Test cleanup of temporary files."""
    downloader = VideoSegmentDownloader()
    downloader.cleanup(temp_dir)
    mock_shutil_rmtree.assert_called_once_with(temp_dir)

def test_download_video(mock_requests_get, mock_subprocess_run, mock_tempfile, mock_shutil_rmtree, mock_path_exists):
    """Test complete video download process."""
    downloader = VideoSegmentDownloader()
    m3u8_url = "https://example.com/video.m3u8"
    output_name = "test_video.mp4"
    
    # Mock the file existence check
    mock_path_exists.return_value = True
    
    output_file = downloader.download_video(m3u8_url, output_name)
    assert output_file is not None
    assert output_file.name == output_name

def test_download_video_with_transcript(mock_requests_get, mock_subprocess_run, mock_tempfile, 
                                      mock_shutil_rmtree, mock_whisper_load_model, mock_path_exists):
    """Test video download with transcript generation."""
    downloader = VideoSegmentDownloader()
    m3u8_url = "https://example.com/video.m3u8"
    output_name = "test_video.mp4"
    
    # Mock the file existence check
    mock_path_exists.return_value = True
    
    output_file = downloader.download_video(m3u8_url, output_name, generate_transcript=True)
    assert output_file is not None
    assert output_file.name == output_name
    mock_whisper_load_model.assert_called_once_with("medium")

def test_error_handling(mock_requests_get):
    """Test error handling."""
    downloader = VideoSegmentDownloader()
    
    # Test invalid URL
    mock_requests_get.side_effect = requests.exceptions.RequestException
    segments = downloader.get_segment_urls("https://example.com/invalid.m3u8")
    assert segments == []

def test_security_checks():
    """Test security-related checks."""
    downloader = VideoSegmentDownloader()
    
    # Test max segments limit
    segments = ["segment{}.ts".format(i) for i in range(1001)]
    limited_segments = segments[:downloader.max_segments]
    assert len(limited_segments) == downloader.max_segments

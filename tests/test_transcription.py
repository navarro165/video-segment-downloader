import pytest
from pathlib import Path
from video_downloader import VideoSegmentDownloader
import whisper
import os

def test_generate_transcript(mock_whisper_load_model, mock_whisper_model, temp_dir):
    """Test transcript generation."""
    downloader = VideoSegmentDownloader()
    
    # Create a mock video file
    video_path = temp_dir / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    
    # Generate transcript
    transcript_path = downloader.generate_transcript(video_path)
    
    assert transcript_path is not None
    assert transcript_path.name == "test_video_transcript.txt"
    assert transcript_path.exists()
    
    # Verify transcript content
    with open(transcript_path, "r") as f:
        content = f.read()
        assert content == "This is a test transcription"

def test_generate_transcript_with_different_model(mock_whisper_load_model, mock_whisper_model, temp_dir):
    """Test transcript generation with different model sizes."""
    downloader = VideoSegmentDownloader()
    
    # Create a mock video file
    video_path = temp_dir / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    
    # Test with different model sizes
    for model_size in ["tiny", "base", "small", "medium", "large"]:
        transcript_path = downloader.generate_transcript(video_path, model_size=model_size)
        assert transcript_path is not None
        mock_whisper_load_model.assert_called_with(model_size)

def test_generate_transcript_error_handling(mock_whisper_load_model, temp_dir):
    """Test error handling in transcript generation."""
    downloader = VideoSegmentDownloader()
    
    # Test with non-existent video file
    video_path = temp_dir / "nonexistent.mp4"
    transcript_path = downloader.generate_transcript(video_path)
    assert transcript_path is None
    
    # Test with invalid model size
    video_path = temp_dir / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    transcript_path = downloader.generate_transcript(video_path, model_size="invalid")
    assert transcript_path is None

def test_transcript_file_encoding(mock_whisper_load_model, mock_whisper_model, temp_dir):
    """Test transcript file encoding."""
    downloader = VideoSegmentDownloader()
    
    # Create a mock video file
    video_path = temp_dir / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    
    # Set up mock model to return special characters
    mock_whisper_model.transcribe.return_value = {"text": "Test with special chars: áéíóú"}
    
    # Generate transcript
    transcript_path = downloader.generate_transcript(video_path)
    
    assert transcript_path is not None
    with open(transcript_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "áéíóú" in content

def test_transcript_file_permissions(mock_whisper_load_model, mock_whisper_model, temp_dir):
    """Test transcript file permissions."""
    downloader = VideoSegmentDownloader()
    
    # Create a mock video file
    video_path = temp_dir / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    
    # Generate transcript
    transcript_path = downloader.generate_transcript(video_path)
    
    assert transcript_path is not None
    assert transcript_path.exists()
    assert transcript_path.is_file()
    # Check if the file is readable using os.access
    assert os.access(transcript_path, os.R_OK), "Transcript file should be readable"

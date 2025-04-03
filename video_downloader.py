#!/usr/bin/env python3
"""
Video Segment Downloader
----------------------
A tool to download videos from streaming services by downloading and combining HLS segments.

This script:
1. Downloads the m3u8 playlist
2. Extracts segment URLs
3. Downloads all video segments
4. Combines them into a single MP4 file using ffmpeg
5. Optionally generates transcripts using Whisper

Requirements:
- Python 3.6+
- requests
- ffmpeg (must be installed on the system)
- whisper (optional, for transcription)
"""

import requests
import os
import re
import subprocess
from typing import List, Optional, Dict
import argparse
from pathlib import Path
import shlex
import tempfile
import logging
from urllib.parse import urlparse
import time
import whisper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoSegmentDownloader:
    def __init__(self, output_dir: str = "downloads"):
        """
        Initialize the video segment downloader.
        
        Args:
            output_dir (str): Directory where downloaded videos will be saved
        """
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Security settings
        self.max_segments = 1000  # Maximum number of segments to download
        self.max_segment_size = 10 * 1024 * 1024  # 10MB per segment
        self.request_timeout = 30  # seconds
        self.verify_ssl = True
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
        }

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to prevent path traversal and other security issues.
        
        Args:
            filename (str): Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Replace path separators with underscores
        filename = filename.replace('/', '_').replace('\\', '_')
        # Remove any path components
        filename = os.path.basename(filename)
        # Remove any potentially dangerous characters
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        # Ensure the filename isn't empty
        if not filename:
            filename = "video"
        return filename

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate a URL to ensure it's safe to use.
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if URL is valid and uses http/https scheme, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False

    @staticmethod
    def parse_curl_command(curl_command: str) -> Dict[str, str]:
        """
        Parse a curl command to extract URL and headers.
        
        Args:
            curl_command (str): The curl command to parse
            
        Returns:
            Dict[str, str]: Dictionary containing URL and headers
        """
        try:
            # Remove 'curl' from the beginning if present
            curl_command = curl_command.strip()
            if curl_command.startswith('curl '):
                curl_command = curl_command[5:].strip()
            
            # Split the command into parts
            parts = shlex.split(curl_command)
            
            # Extract URL (first argument that doesn't start with '-')
            url = next((part for part in parts if not part.startswith('-')), None)
            
            # Extract headers
            headers = {}
            for i, part in enumerate(parts):
                if part == '-H':
                    header = parts[i + 1].strip("'")
                    if ':' in header:
                        key, value = header.split(':', 1)
                        headers[key.strip()] = value.strip()
            
            return {
                'url': url,
                'headers': headers
            }
        except Exception as e:
            logger.error(f"Error parsing curl command: {str(e)}")
            return {'url': None, 'headers': {}}

    def get_segment_urls(self, m3u8_url: str, custom_headers: Optional[Dict[str, str]] = None) -> List[str]:
        """
        Get all segment URLs from the m3u8 playlist.
        
        Args:
            m3u8_url (str): URL of the m3u8 playlist
            custom_headers (Optional[Dict[str, str]]): Custom headers to use
            
        Returns:
            List[str]: List of segment URLs
        """
        if not self.validate_url(m3u8_url):
            logger.error("Invalid m3u8 URL provided")
            return []

        headers = custom_headers if custom_headers else self.headers
        try:
            response = requests.get(
                m3u8_url,
                headers=headers,
                timeout=self.request_timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            content = response.text
            logger.debug("M3U8 playlist content: %s", content[:500])
            
            # Look for .ts files in the playlist
            segments = []
            for line in content.splitlines():
                if line.endswith('.ts'):
                    segments.append(line.strip())
            
            if not segments:
                logger.warning("No .ts segments found in the playlist")
                # Try to find the master playlist URL
                for line in content.splitlines():
                    if line.endswith('.m3u8'):
                        master_url = line.strip()
                        if not master_url.startswith('http'):
                            # Handle relative URLs
                            base_url = m3u8_url.rsplit('/', 1)[0]
                            master_url = f"{base_url}/{master_url}"
                        logger.info(f"Found master playlist URL: {master_url}")
                        # Recursively get segments from the master playlist
                        return self.get_segment_urls(master_url, custom_headers)
            
            return segments[:self.max_segments]  # Limit number of segments
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading m3u8 playlist: {str(e)}")
            return []

    def download_segments(self, segments: List[str], base_url: str, output_name: str, custom_headers: Optional[Dict[str, str]] = None) -> Optional[Path]:
        """
        Download all video segments.
        
        Args:
            segments (List[str]): List of segment filenames
            base_url (str): Base URL for the segments
            output_name (str): Name for the output video file
            custom_headers (Optional[Dict[str, str]]): Custom headers to use
            
        Returns:
            Optional[Path]: Path to the segments directory if successful, None otherwise
        """
        if not segments:
            logger.error("No segments to download")
            return None

        try:
            # Create a secure temporary directory
            segments_dir = Path(tempfile.mkdtemp(prefix="video_segments_"))
            
            headers = custom_headers if custom_headers else self.headers
            
            for i, segment in enumerate(segments):
                # Handle relative URLs
                if segment.startswith('/'):
                    segment_url = f"https://embed-cloudfront.wistia.com{segment}"
                else:
                    segment_url = f"{base_url}/{segment}"
                    
                logger.info(f"Downloading segment {i+1}/{len(segments)}")
                
                try:
                    segment_response = requests.get(
                        segment_url,
                        headers=headers,
                        timeout=self.request_timeout,
                        verify=self.verify_ssl,
                        stream=True
                    )
                    segment_response.raise_for_status()
                    
                    # Check content length
                    content_length = int(segment_response.headers.get('content-length', 0))
                    if content_length > self.max_segment_size:
                        logger.warning(f"Segment {i+1} exceeds maximum size limit")
                        continue
                    
                    # Download with progress tracking
                    segment_path = segments_dir / f"segment_{i:03d}.ts"
                    with open(segment_path, 'wb') as f:
                        downloaded = 0
                        for chunk in segment_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if downloaded > self.max_segment_size:
                                    logger.warning(f"Segment {i+1} download exceeded size limit")
                                    break
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error downloading segment {i+1}: {str(e)}")
                    continue
            
            return segments_dir
            
        except Exception as e:
            logger.error(f"Error in download_segments: {str(e)}")
            return None

    def combine_segments(self, segments_dir: Path, output_name: str) -> Optional[Path]:
        """
        Combine all segments into a single MP4 file using ffmpeg.
        
        Args:
            segments_dir (Path): Directory containing the segments
            output_name (str): Name for the output video file (can include extension)
            
        Returns:
            Optional[Path]: Path to the output video file if successful, None otherwise
        """
        try:
            # Sanitize output filename
            output_name = self.sanitize_filename(output_name)
            if not output_name.lower().endswith('.mp4'):
                output_name = f"{output_name}.mp4"
            
            output_file = self.output_dir / output_name
            
            # Create a file list for ffmpeg
            file_list = segments_dir / "file_list.txt"
            with open(file_list, 'w') as f:
                for i in range(len(list(segments_dir.glob("segment_*.ts")))):
                    # Write absolute paths to the segments
                    segment_path = segments_dir / f"segment_{i:03d}.ts"
                    f.write(f"file '{segment_path.absolute()}'\n")
            
            # Run ffmpeg with proper argument escaping
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(file_list.absolute()),
                '-c', 'copy',
                str(output_file.absolute())
            ]
            
            subprocess.run(
                cmd,
                check=True,
                timeout=300  # 5 minutes timeout
            )
            return output_file
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error combining video segments: {str(e)}")
            return None
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg operation timed out")
            return None
        except FileNotFoundError:
            logger.error("ffmpeg is not installed. Please install ffmpeg to combine the video segments.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in combine_segments: {str(e)}")
            return None

    def cleanup(self, segments_dir: Path) -> None:
        """
        Clean up temporary files and directories after successful download.
        
        Args:
            segments_dir (Path): Directory containing the segments to clean up
        """
        try:
            if segments_dir.exists():
                import shutil
                shutil.rmtree(segments_dir)
                logger.info(f"Cleaned up temporary files in {segments_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

    def generate_transcript(self, video_path: Path, model_size: str = "medium") -> Optional[Path]:
        """
        Generate a transcript for the video using Whisper.
        
        Args:
            video_path (Path): Path to the video file
            model_size (str): Size of the Whisper model to use (tiny, base, small, medium, large)
            
        Returns:
            Optional[Path]: Path to the transcript file if successful, None otherwise
        """
        try:
            # Check if video file exists
            if not video_path.exists():
                logger.error(f"Video file not found: {video_path}")
                return None
                
            # Validate model size
            valid_models = ["tiny", "base", "small", "medium", "large"]
            if model_size not in valid_models:
                logger.error(f"Invalid model size. Must be one of: {', '.join(valid_models)}")
                return None
            
            logger.info(f"Loading Whisper model ({model_size})...")
            model = whisper.load_model(model_size)
            
            logger.info("Generating transcript...")
            result = model.transcribe(str(video_path))
            
            # Create transcript file path
            transcript_path = video_path.parent / f"{video_path.stem}_transcript.txt"
            
            # Save the transcript
            logger.info(f"Saving transcript to {transcript_path}")
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(result["text"])
            
            return transcript_path
            
        except Exception as e:
            logger.error(f"Error generating transcript: {str(e)}")
            return None

    def download_video(self, m3u8_url: str, output_name: str, custom_headers: Optional[Dict[str, str]] = None, generate_transcript: bool = False) -> Optional[Path]:
        """
        Download and combine a video from segments.
        
        Args:
            m3u8_url (str): URL of the m3u8 playlist
            output_name (str): Name for the output video file (can include extension)
            custom_headers (Optional[Dict[str, str]]): Custom headers to use
            generate_transcript (bool): Whether to generate a transcript for the video
            
        Returns:
            Optional[Path]: Path to the output video file if successful, None otherwise
        """
        try:
            # Get segment URLs
            segments = self.get_segment_urls(m3u8_url, custom_headers)
            if not segments:
                logger.error("No segments found in the m3u8 playlist")
                return None
                
            # Use the directory part of the m3u8 URL as the base URL
            base_url = m3u8_url.rsplit('/', 1)[0]
            logger.info(f"Base URL for segments: {base_url}")
            
            # Create a temporary directory name for segments
            temp_dir_name = f"temp_{self.sanitize_filename(output_name)}"
            
            # Download segments
            segments_dir = self.download_segments(segments, base_url, temp_dir_name, custom_headers)
            if not segments_dir:
                logger.error("Failed to download segments")
                return None
                
            logger.info(f"Downloaded {len(segments)} segments successfully")
            
            # Combine segments
            logger.info("Combining segments into a single video file...")
            output_file = self.combine_segments(segments_dir, output_name)
            
            if output_file and output_file.exists():
                logger.info(f"Video has been successfully saved as '{output_file}'")
                
                # Generate transcript if requested
                if generate_transcript:
                    logger.info("Generating transcript...")
                    transcript_path = self.generate_transcript(output_file)
                    if transcript_path:
                        logger.info(f"Transcript has been saved as '{transcript_path}'")
                
                # Clean up temporary files
                self.cleanup(segments_dir)
                return output_file
            return None
            
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return None

def main():
    parser = argparse.ArgumentParser(description="Download videos from streaming services")
    parser.add_argument("input", help="URL of the m3u8 playlist or curl command")
    parser.add_argument("--output-name", "-o", help="Name for the output video file (can include extension)")
    parser.add_argument("--output-dir", "-d", help="Directory where videos will be saved", default="downloads")
    parser.add_argument("--curl", "-c", action="store_true", help="Input is a curl command")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--transcript", "-t", action="store_true", help="Generate transcript for the video")
    parser.add_argument("--transcript-model", help="Whisper model size for transcription (tiny, base, small, medium, large)", default="medium")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    downloader = VideoSegmentDownloader(output_dir=args.output_dir)
    
    # If no output name is provided, prompt the user
    if not args.output_name:
        args.output_name = input("Enter a name for the output video file (without extension): ")
        if not args.output_name:
            args.output_name = "video"
        if not args.output_name.lower().endswith('.mp4'):
            args.output_name = f"{args.output_name}.mp4"
    
    if args.curl:
        # Parse curl command
        parsed = downloader.parse_curl_command(args.input)
        if not parsed['url']:
            logger.error("Could not extract URL from curl command")
            return
        
        # Extract m3u8 URL from the segment URL by removing the segment part
        m3u8_url = parsed['url'].rsplit('/seg-', 1)[0]
        custom_headers = parsed['headers']
        
        logger.info(f"Using m3u8 URL: {m3u8_url}")
        
        # Download the video
        downloader.download_video(m3u8_url, args.output_name, custom_headers, args.transcript)
    else:
        # Direct URL input
        downloader.download_video(args.input, args.output_name, generate_transcript=args.transcript)

if __name__ == "__main__":
    main() 
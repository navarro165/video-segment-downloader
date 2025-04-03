# Video Segment Downloader

A Python tool for downloading videos from streaming services by downloading and combining HLS segments. This tool is particularly useful when you have a curl command for a video segment and want to download the complete video. Supports automatic transcription using OpenAI's Whisper.

## Features

- Downloads video segments from m3u8 playlists
- Combines segments into a single MP4 file
- Supports custom output filenames (with interactive prompt)
- Automatic cleanup of temporary files
- Progress tracking during download
- Error handling and retry mechanisms
- Supports custom headers (via curl command)
- Automatic transcription using OpenAI's Whisper (optional)
- Progress logging and error handling
- Secure file handling and cleanup

## Requirements

- Python 3.6+
- Required Python packages (install using `pip install -r requirements.txt`):
  - requests
  - openai-whisper (optional, for transcription)
  - tqdm
- ffmpeg (must be installed on your system)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/navarro165/video-segment-downloader.git
cd video-segment-downloader
```

2. Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Make sure ffmpeg is installed on your system:
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

5. (Optional) Install Whisper for transcription:
```bash
pip install openai-whisper
```

## Usage

1. Copy a curl command from your browser's network tab for a video segment request
2. Run the script with the curl command:
```bash
python video_downloader.py "curl 'https://...'" --curl
```

3. The script will:
   - Extract the m3u8 playlist URL from the segment URL
   - Prompt you for an output filename (if not provided)
   - Download all video segments
   - Combine them into a single MP4 file
   - Save the video in the downloads directory

4. Or specify a custom output filename:
```bash
python video_downloader.py "curl 'https://...'" --curl --output "my_video.mp4"
```

5. To generate a transcript for the downloaded video:
```bash
python video_downloader.py "curl 'https://...'" --curl --transcript
```

You can specify the Whisper model size (default is "medium"):
```bash
python video_downloader.py "curl 'https://...'" --curl --transcript --transcript-model base
```

Available model sizes:
- `tiny`: Fastest, least accurate
- `base`: Good balance of speed and accuracy
- `small`: More accurate but slower
- `medium`: Even more accurate but slower
- `large`: Most accurate but slowest

### Batch Transcription

To transcribe existing videos in the downloads directory:
```bash
python transcribe_videos.py
```

## How It Works

1. The script extracts the m3u8 playlist URL from the provided curl command
2. Downloads all video segments listed in the playlist
3. Combines the segments into a single MP4 file using ffmpeg
4. Optionally generates a transcript using Whisper
5. Cleans up temporary files automatically

## Error Handling

- The script includes retry mechanisms for failed downloads
- Temporary files are cleaned up even if the download fails
- Detailed error messages are provided for troubleshooting

## Notes

- The first time you use transcription, it will download the Whisper model (size varies by model)
- Transcription speed depends on your CPU/GPU and the model size chosen
- For non-English videos, Whisper will automatically detect and transcribe in the source language

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
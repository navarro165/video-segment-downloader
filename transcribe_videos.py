import os
import whisper
from pathlib import Path

def transcribe_videos():
    # Initialize the Whisper model
    print("Loading Whisper model...")
    model = whisper.load_model("base")
    
    # Get the downloads directory
    downloads_dir = Path("downloads")
    
    # Process each video file
    for video_file in downloads_dir.glob("*.mp4"):
        print(f"\nProcessing {video_file.name}...")
        
        # Create output filename
        output_file = downloads_dir / f"{video_file.stem}_transcript.txt"
        
        # Transcribe the video
        print("Transcribing...")
        result = model.transcribe(str(video_file))
        
        # Save the transcript
        print(f"Saving transcript to {output_file}")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result["text"])
        
        print(f"Completed {video_file.name}")

if __name__ == "__main__":
    transcribe_videos() 
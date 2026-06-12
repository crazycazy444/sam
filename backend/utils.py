import os
import yt_dlp
import whisper
from gtts import gTTS
import uuid

def download_video(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    clip_id = str(uuid.uuid4())
    # Use a simpler template to avoid issues
    filepath = os.path.join(output_dir, f"{clip_id}.mp4")

    import imageio_ffmpeg
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': filepath,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': ffmpeg_path
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filepath

def transcribe_video(filepath):
    # Using 'tiny' for speed in this environment
    model = whisper.load_model("tiny")
    result = model.transcribe(filepath)
    return result

def get_viral_segments(transcription, min_duration=15, max_duration=30):
    segments = []
    text_segments = transcription.get('segments', [])

    if not text_segments:
        return []

    current_start = text_segments[0]['start']
    current_end = current_start
    current_text = ""

    for seg in text_segments:
        duration = seg['end'] - current_start
        if duration < max_duration:
            current_end = seg['end']
            current_text += " " + seg['text']
        else:
            if (current_end - current_start) >= min_duration:
                segments.append({
                    'start': current_start,
                    'end': current_end,
                    'text': current_text.strip()
                })
            current_start = seg['start']
            current_end = seg['end']
            current_text = seg['text']

    if current_text and (current_end - current_start) >= min_duration:
        segments.append({
            'start': current_start,
            'end': current_end,
            'text': current_text.strip()
        })

    return segments

def create_tts(text, output_path):
    tts = gTTS(text=text, lang='en')
    tts.save(output_path)
    return output_path

def generate_srt(segments, output_path):
    def format_time(seconds):
        ms = int((seconds - int(seconds)) * 1000)
        s = int(seconds) % 60
        m = (int(seconds) // 60) % 60
        h = int(seconds) // 3600
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(output_path, "w") as f:
        for i, seg in enumerate(segments):
            f.write(f"{i+1}\n")
            f.write(f"{format_time(seg['start']) if i > 0 else format_time(0)} --> {format_time(seg['end'] - segments[0]['start'])}\n")
            f.write(f"{seg['text'].strip()}\n\n")

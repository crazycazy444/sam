import os
import subprocess
import imageio_ffmpeg
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
from .utils import create_tts, generate_srt
import uuid

# Set the FFMPEG path for moviepy
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe

def process_clip(video_path, start_time, end_time, text, transcription_segments, output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)
    clip_id = str(uuid.uuid4())
    temp_video_path = os.path.join(output_dir, f"temp_{clip_id}.mp4")
    output_filename = f"{clip_id}.mp4"
    output_path = os.path.join(output_dir, output_filename)

    # 1. Cut and Crop the video using MoviePy
    full_video = VideoFileClip(video_path)
    video = full_video.subclipped(start_time, end_time)

    w, h = video.size
    target_ratio = 9/16
    current_ratio = w/h

    if current_ratio > target_ratio:
        new_w = h * target_ratio
        video = video.cropped(x_center=w/2, width=new_w)
    else:
        new_h = w / target_ratio
        video = video.cropped(y_center=h/2, height=new_h)

    # 2. Add Voice Cover (TTS)
    tts_filename = f"{clip_id}.mp3"
    tts_path = os.path.join(output_dir, tts_filename)
    create_tts(text, tts_path)

    tts_audio = AudioFileClip(tts_path)
    if video.audio:
        final_audio = CompositeAudioClip([video.audio.with_volume_scaled(0.2), tts_audio.with_volume_scaled(1.0)])
    else:
        final_audio = tts_audio

    video = video.with_audio(final_audio)

    # Write intermediate video before adding subtitles with ffmpeg
    video.write_videofile(temp_video_path, codec="libx264", audio_codec="aac")
    video.close()
    full_video.close()

    # 3. Add Subtitles using FFmpeg and SRT
    srt_path = os.path.join(output_dir, f"{clip_id}.srt")
    # Filter segments to only include those within the clip
    clip_segments = [s for s in transcription_segments if s['start'] >= start_time and s['end'] <= end_time]
    if not clip_segments:
        # Fallback to the whole text if no fine-grained segments
        clip_segments = [{'start': start_time, 'end': end_time, 'text': text}]

    generate_srt(clip_segments, srt_path)

    # Use ffmpeg to burn subtitles
    # Note: subtitles filter needs escaped path on windows, but here we are on linux
    # Also we need to specify font size and position in the filter if possible,
    # but basic burning is a good start.
    try:
        subprocess.run([
            ffmpeg_exe, "-i", temp_video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&H00FFFF,Alignment=2'",
            "-c:a", "copy", output_path
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg subtitle error: {e.stderr.decode()}")
        # Fallback to temp video if subtitle burning fails
        os.rename(temp_video_path, output_path)

    # Cleanup
    if os.path.exists(temp_video_path): os.remove(temp_video_path)
    if os.path.exists(tts_path): os.remove(tts_path)
    if os.path.exists(srt_path): os.remove(srt_path)

    return output_filename

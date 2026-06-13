from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import uuid
from .utils import download_video, transcribe_video, get_viral_segments
from .processor import process_clip

app = FastAPI()

# Store job status in memory (use Redis for production)
jobs = {}

class VideoRequest(BaseModel):
    url: str

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

async def run_processing_task(job_id: str, url: str):
    jobs[job_id] = {"status": "downloading", "clips": []}
    try:
        # Use /tmp for serverless environments
        tmp_dir = "/tmp"
        downloads_dir = os.path.join(tmp_dir, "downloads")
        outputs_dir = "/tmp/outputs"

        # 1. Download
        video_path = download_video(url, output_dir=downloads_dir)

        # 2. Transcribe
        jobs[job_id]["status"] = "transcribing"
        transcription = transcribe_video(video_path)

        # 3. Identify segments
        jobs[job_id]["status"] = "segmenting"
        segments = get_viral_segments(transcription)

        # 4. Process clips
        jobs[job_id]["status"] = "processing_clips"
        processed_clips = []
        for i, seg in enumerate(segments):
            if i >= 3: break

            clip_filename = process_clip(
                video_path,
                seg['start'],
                seg['end'],
                seg['text'],
                transcription.get('segments', []),
                output_dir=outputs_dir
            )
            processed_clips.append({
                "filename": clip_filename,
                "url": f"/outputs/{clip_filename}",
                "text": seg['text']
            })
            jobs[job_id]["clips"] = processed_clips

        jobs[job_id]["status"] = "completed"

        if os.path.exists(video_path):
            os.remove(video_path)

    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

@app.post("/api/process")
async def process_video(request: VideoRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(run_processing_task, job_id, request.url)
    return {"job_id": job_id}

# In a real Vercel deployment, outputs would be uploaded to S3/Cloudinary.
# Here we ensure the directory exists for local testing/demonstration.
@app.on_event("startup")
async def startup_event():
    os.makedirs("/tmp/outputs", exist_ok=True)

if os.path.exists("/tmp/outputs"):
    app.mount("/outputs", StaticFiles(directory="/tmp/outputs"), name="outputs")

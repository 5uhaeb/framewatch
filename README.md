# Framewatch

A Taskflow-styled video review frontend with a local MoBiLSTM inference bridge. Dark mode is the default. The original cartoon-hybrid CSS was reused from the user's Taskflow project.

## Run locally

Requirements: Node.js 20.19+ and Python 3.13 on this machine. TensorFlow runs on the CPU on native Windows.

From `framewatch/backend`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8016
```

In a second terminal, from `framewatch/frontend`:

```powershell
npm ci
npm run dev
```

Open **http://127.0.0.1:5186**. The Vite proxy connects `/api` to port 8016.

## Demo sign-in

- Email: `xyz@gmail.com`
- Password: `12345678`
- The Google button opens a clearly labeled simulated sign-in. It does not contact Google. Registration is not needed.

Authentication is intentionally a frontend demonstration, as requested. It does not protect backend endpoints and must not be treated as a production account system. The backend binds to loopback by default.

## Video and markers

- Open a local video or drag it onto the workspace. Playback uses an object URL; normal playback does not upload the file.
- Direct HTTP/HTTPS video links, HLS (`.m3u8`), and DASH (`.mpd`) are supported when the browser and source permit playback.
- Native video controls provide playback, audio volume, fullscreen, playback speed, and seeking, according to browser support.
- A YouTube link opens an embedded player; embedded frames cannot be analyzed because of browser isolation.
- For a browser-incompatible local container or codec, **Convert local video** sends the file to the configured backend. FFmpeg converts it to H.264/AAC MP4. Files are limited to 1 GB; temporary converted copies expire after one hour and are cleaned on startup, conversion, or expired-file access.
- DRM, RTSP, arbitrary web-page URLs, unavailable streams, and sources that block browser access cannot be universally played. Conversion does not bypass access restrictions.
- **Start detection** samples 16 RGB frames, at approximately 4 frames per second, and sends each batch to the model service. Sampling pauses while inference is in flight. This is playback-time review, not an exhaustive offline scan of every frame.
- Flags appear as clickable markers below the video and as timestamp cards. Seeking pauses detection to avoid mixing unrelated frames; restart it at the new location.
- **Mark moment** adds a manual review bookmark. Markers can be exported to JSON, deleted individually, or cleared for the current video.
- Markers are stored per source in `sessionStorage`, with a six-hour expiry. They persist through refresh in the same tab but are not durable records. Local files must be reopened after refresh. Nothing is preloaded with fake detections.

## Model profile

The provided `MoBiLSTM_model (1).zip` is a Keras archive containing configuration and weights, not an HTTP backend. It is copied without modification to `backend/models/mobilstm.keras`.

Verified from the supplied artifact:

- Input: `(batch, 16, 64, 64, 3)`.
- MobileNetV2 frame encoder, bidirectional LSTM, and dense layers.
- Output: two softmax scores.
- Model loads and executes in the included local service.

**Class order, preprocessing, training frame rate, label names, and calibration were not included.** They cannot be inferred reliably from unlabeled weights. The initial profile assumes class 1 is the flagged class and input is scaled to 0–1. These assumptions are visible and editable under **Model settings**, including MobileNetV2-style −1–1 scaling and raw RGB. Both raw output scores are returned by the API. Results are labeled as unverified review candidates, not proof of an anomaly or crime. Confirm the training profile with the model author before evaluating accuracy.

The initial threshold is 80%. This is an uncalibrated model score threshold, not an established probability of a crime. Nearby model flags are grouped. Changing the inference profile affects subsequent flags; existing markers retain the profile used to create them.

## Model service

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Model readiness and declared input shape |
| `POST /api/predict` | Infer one batch of 16 small base64 RGB frames |
| `POST /api/convert` | Multipart local-video conversion |
| `GET /api/media/{key}` | Temporary converted playback, with byte-range support |

The frontend can connect to a different service origin from Model settings. Allow that frontend origin through `FRONTEND_ORIGINS` on the backend, as a comma-separated list. Only select a service you trust with sampled frames and conversion uploads.

The hosted frontend is a private static preview. TensorFlow and FFmpeg run in the local backend, not on static hosting. Use the local app for the complete workflow; a hosted frontend needs a reachable inference service and suitable CORS/TLS configuration.

## Verification

`qa/check_ui.py` checks demo login, local playback with audio, actual model responses, marker creation, seeking, session restore, clearing, theme switching, and mobile overflow. The generated video uses a test pattern with a sine-wave audio track; it is not an accuracy benchmark. `qa/check_service.py` checks input validation and real FFmpeg conversion with retained audio.

```powershell
python qa/check_ui.py
python qa/check_service.py
```

Build the static frontend with `npm run build` from `frontend/`. The production bundle is written to the root `dist/` directory.

## Reference documentation

- [HLS.js playback and cross-origin requirements](https://github.com/video-dev/hls.js)
- [Google Identity server-side verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token), for a future replacement of the requested demo login


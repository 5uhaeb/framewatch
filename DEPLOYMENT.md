# Deployment

Deploy the Python backend on Render using the root `render.yaml` blueprint. Deploy Vercel with **Root Directory: frontend**; `frontend/vercel.json` declares the build and output directory.

1. Create the Render web service from this repository. It uses `backend/`, Python 3.13, `pip install -r requirements.txt`, and `uvicorn main:app --host 0.0.0.0 --port $PORT`.
2. Set `VITE_API_URL` on the Vercel project to the actual Render service origin (for example, `https://your-service.onrender.com`), then deploy or redeploy the frontend.
3. Set Render's `FRONTEND_ORIGINS` to the actual Vercel production origin. Multiple exact origins can be comma-separated. Redeploy or restart the service after updating it.
4. Check the Render `/api/health` endpoint. `status: ready` confirms that the model loaded. The frontend must show Model connected before inference can start.

The free Render plan is selected to avoid an unapproved paid service. TensorFlow may exceed its available memory; if the process is terminated, review Render logs and choose an appropriately sized instance with the account owner's approval. First builds and cold starts can take several minutes.

Demo credentials are intentionally public prototype credentials, not real authentication. Do not treat the hosted backend as access-controlled. Model labels and preprocessing remain unverified as described in the README.

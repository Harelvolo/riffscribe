# Deploying Riffscribe

This is the exact, ordered checklist to get Riffscribe live on the internet.
Everything code-related is already done - the steps below are the parts that
need your own accounts/payment, which nobody else can do for you.

Rough cost: ~$10-15/year for the domain, ~5€/month (~$5.50) for the server.

## 1. Push the code to GitHub

The project already has a local git repo with an initial commit
(`git log` in the project root shows it). You just need to put it on GitHub:

1. Go to github.com, sign in (or create a free account), click "New repository".
2. Name it `riffscribe` (private or public, your choice). Don't initialize
   with a README/gitignore - the project already has them.
3. Back in your terminal, in the `guitar-solo-tabs` folder, run the two
   commands GitHub shows you on the new repo page, which will look like:
   ```
   git remote add origin https://github.com/YOUR_USERNAME/riffscribe.git
   git push -u origin main
   ```

## 2. Buy a domain (~$10-15/year)

1. Go to Cloudflare's registrar (domains.cloudflare.com) - it sells at cost
   with no markup, the cheapest option. (Namecheap is a fine alternative.)
2. Search for `riffscribe.com` (or `.app` / `.io` if `.com` is taken) and buy it.
3. If it's not already on Cloudflare, add the domain to your Cloudflare
   account (Cloudflare gives every domain free DNS + free SSL).

## 3. Frontend: Cloudflare Pages (free)

1. In the Cloudflare dashboard, go to Workers & Pages -> Create -> Pages ->
   Connect to Git.
2. Pick your `riffscribe` GitHub repo.
3. Build settings:
   - Framework preset: Vite
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Root directory: `frontend`
4. Add an environment variable: `VITE_API_BASE_URL` = `https://api.riffscribe.com`
   (use your real domain; this is the backend subdomain from step 5).
5. Deploy. Cloudflare gives you a `*.pages.dev` URL immediately - test it works.
6. In the Pages project's "Custom domains" tab, add your real domain
   (e.g. `riffscribe.com` and `www.riffscribe.com`).

## 4. Backend: a small VPS (Hetzner, ~5€/month)

1. Go to hetzner.com, create an account, add a payment method.
2. Create a new Cloud server: cheapest **CX22** plan (2 vCPU, 4GB RAM) is
   plenty - Ubuntu 24.04 image, closest region to your users.
3. SSH into the server (Hetzner gives you the IP + root password, or set up
   an SSH key during creation):
   ```
   ssh root@YOUR_SERVER_IP
   ```
4. Install Docker:
   ```
   curl -fsSL https://get.docker.com | sh
   ```
5. Install git and clone your repo:
   ```
   apt-get install -y git
   git clone https://github.com/YOUR_USERNAME/riffscribe.git
   cd riffscribe/backend
   ```
6. Build and run the backend container:
   ```
   docker build -t riffscribe-backend .
   docker run -d --name riffscribe-backend \
     -p 8000:8000 \
     -v /root/riffscribe-storage:/app/storage \
     -e ALLOWED_ORIGIN=https://riffscribe.com \
     -e PUBLIC_BASE_URL=https://api.riffscribe.com \
     -e GOOGLE_CLIENT_ID=651346554893-00th83636jf0mmc6t0b57ghfg6p3mm1h.apps.googleusercontent.com \
     --restart unless-stopped \
     riffscribe-backend
   ```
   (`-v /root/riffscribe-storage:/app/storage` is important - it keeps your
   database/uploads/tabs on the server's real disk, surviving container
   restarts and redeploys.)
7. Check it's running: `curl http://localhost:8000/api/health` should return
   `{"status":"ok"}`.

## 5. Point a subdomain at the backend + get HTTPS (Caddy)

1. In Cloudflare DNS for your domain, add an **A record**: name `api`,
   value = your Hetzner server's IP address (uncheck the orange "proxy" cloud
   for this record - DNS-only - so Caddy can issue its own certificate).
2. On the server, install Caddy (handles HTTPS automatically, zero config):
   ```
   apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
   apt-get update && apt-get install -y caddy
   ```
3. Edit `/etc/caddy/Caddyfile` to:
   ```
   api.riffscribe.com {
       reverse_proxy localhost:8000
   }
   ```
4. Restart Caddy: `systemctl restart caddy`. Within a minute, Caddy fetches a
   free Let's Encrypt certificate automatically.
5. Test from your own machine: `curl https://api.riffscribe.com/api/health`
   should return `{"status":"ok"}`.

## 6. Update Google OAuth settings

Google Sign-In only works from domains you've explicitly authorized:

1. Go to console.cloud.google.com -> APIs & Services -> Credentials.
2. Open your OAuth 2.0 Client ID (the one already in `google_client_id.txt`).
3. Under "Authorized JavaScript origins", add `https://riffscribe.com` (and
   `https://www.riffscribe.com` if you're using the www version).
4. Save.

## 7. Final check

Visit `https://riffscribe.com` in a normal browser (not this dev environment)
and run through the whole flow once: upload a song, sign in with Google,
generate a solo, refresh the page. If anything looks off, the most likely
culprits are a typo in `VITE_API_BASE_URL`/`ALLOWED_ORIGIN`/`PUBLIC_BASE_URL`,
or the Google OAuth origin not being saved yet (can take a few minutes).

## If it takes off and the free-tier VPS starts to struggle

The CX22 plan should comfortably handle real traffic for a while. If it ever
becomes the bottleneck, Hetzner lets you resize to a bigger plan in a couple
of clicks with a short restart - no re-deployment needed.

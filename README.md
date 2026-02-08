# plantopo-tiles

A containerized deployment of MapProxy to serve Ordnance Survey Leisure maps
reprojected from British National Grid (EPSG:27700) to Web Mercator (EPSG:3857).

Provides Podman deployment using Quadlet with persistent cache, plus Docker
Compose for integration testing.

## Development

mapproxy: http://localhost:3010 tile viewer: http://localhost:3011

* `./dev.sh` Run development servers
* `./test.sh` Run integration tests

See also notes.txt

## Production Deployment (Podman Quadlet + systemd)

On my personal server

**Setup:**
1. `git clone https://github.com/dzfranklin/plantopo-tiles.git`
2. Generate tokens and add to /etc/caddy/environment:
   ```bash
  python3 -c "import secrets, string; print(''.join(secrets.choice(string.digits + string.ascii_lowercase) for _ in range(32)))"
   ```
3. Append infra/Caddyfile to /etc/caddy/Caddyfile
4. Create ~/.config/plantopo-tiles/env

**Deploy**
1. `sudo su app`
2. `cd ~/plantopo-tiles`
3. `git pull && ./deploy.sh`

## Integration Testing

Run integration tests with Docker Compose:

```bash
./test.sh
```

## Usage

Once deployed, access the service at `http://localhost:8080`

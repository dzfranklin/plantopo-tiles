# plantopo-tiles

A containerized deployment of MapProxy to serve Ordnance Survey Leisure maps
reprojected from British National Grid (EPSG:27700) to Web Mercator (EPSG:3857).

Provides Podman deployment using Quadlet with persistent cache, plus Docker
Compose for integration testing.

## Development

* `./dev.sh` Run development server, see http://localhost:3010
* `dev.sh --prod-server`
* `./test.sh` Run integration tests

See also notes.txt

## Production Deployment (Podman Quadlet + systemd)

TODO

## Integration Testing

Run integration tests with Docker Compose:

```bash
export OS_API_KEY=your_api_key_here
docker-compose up --build test
```

## Usage

Once deployed, access the service at `http://localhost:8080`

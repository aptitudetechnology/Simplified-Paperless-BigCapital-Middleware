build:
	docker build -t caston81/simplified-paperless-bigcapital-middleware:latest -f docker/Dockerfile .

run: build
	docker run --name simplified-paperless-middleware --rm -p 5000:5000 caston81/simplified-paperless-bigcapital-middleware:latest

run-d: build
	docker run -d --name simplified-paperless-middleware -p 5000:5000 caston81/simplified-paperless-bigcapital-middleware:latest

debug:
	docker run -it --rm --name simplified-paperless-middleware-debug caston81/simplified-paperless-bigcapital-middleware:latest bash

clean:
	docker stop simplified-paperless-middleware || true
	docker rm simplified-paperless-middleware || true
	docker rmi caston81/simplified-paperless-bigcapital-middleware:latest || true

# --- Docker Compose related targets ---

compose-up: build
	docker-compose -f docker/docker-compose.yml up -d

compose-down:
	docker-compose -f docker/docker-compose.yml down

compose-logs:
	docker-compose -f docker/docker-compose.yml logs -f

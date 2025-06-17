build:
	docker build -t simplified-paperless-bigcapital-middleware -f docker/Dockerfile .

run: build
	docker run --rm -p 5000:5000 simplified-paperless-bigcapital-middleware


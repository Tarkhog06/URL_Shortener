# URL_Shortener

This application aim to let me learn in good way docker.

## Functional features

- User submits a long URL
- Application generates a unique short code
- Store the mapping in a database
- Visiting the short URL redirects to the original URL

## Non-functional features

- Easy deployment with Docker

## Workflow

Browser -> Reverse Proxy -> Backend -> BDD

## Technologies

- Reverse Proxy (Nginx)
- Backend (FastAPI)
- BDD (PostgreSQL)

## How to use Docker ?
- build: docker build -t url-shortener ./backend
- run: docker run --rm -d --name urlshort-api -p 3000:8000 url-shortener 
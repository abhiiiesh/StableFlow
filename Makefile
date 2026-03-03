.PHONY: dev build up down test logs clean

## ── Development ──────────────────────────────────────────────────────────────

dev:		## Run API locally (no Docker)
	uvicorn main:app --reload --port 8000

install:	## Install Python dependencies
	pip install -r requirements.txt

## ── Docker ───────────────────────────────────────────────────────────────────

build:		## Build Docker image
	docker-compose build

up:		## Start all services
	docker-compose up -d
	@echo ""
	@echo "✅ StableFlow is running!"
	@echo "   API:              http://localhost:8000"
	@echo "   Swagger docs:     http://localhost:8000/docs"
	@echo "   ReDoc:            http://localhost:8000/redoc"
	@echo "   Webhook tester:   http://localhost:9000"

down:		## Stop all services
	docker-compose down

logs:		## Tail API logs
	docker-compose logs -f api

restart:	## Restart API container
	docker-compose restart api

## ── Testing ──────────────────────────────────────────────────────────────────

test:		## Run full test suite
	pytest tests/ -v --tb=short

test-routing:	## Run routing engine tests only
	pytest tests/test_all.py::TestRoutingEngine tests/test_all.py::TestComplianceEngine -v

test-api:	## Run API integration tests only
	pytest tests/test_all.py::TestPaymentAPI tests/test_all.py::TestRoutingAPI -v

## ── Utilities ────────────────────────────────────────────────────────────────

clean:		## Remove containers, volumes, cache
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

demo-route:	## Test the routing engine with a sample request
	curl -s -X POST http://localhost:8000/api/v1/routing/route \
	  -H "Content-Type: application/json" \
	  -d '{"sender_country":"US","receiver_country":"IN","amount_usd":500,"token":"USDT","strategy":"balanced","include_explanation":true}' \
	  | python3 -m json.tool

demo-payment:	## Create a sample payment intent (set MERCHANT_ID first)
	curl -s -X POST http://localhost:8000/api/v1/payments/intent \
	  -H "Content-Type: application/json" \
	  -d '{"merchant_id":"demo","amount":100,"token":"USDT","description":"Demo order"}' \
	  | python3 -m json.tool

# LexiFlow AI Inference Gateway

A standalone Java 21 / Spring Boot gateway in front of the existing Python FastAPI dictionary service. It is intentionally a separate deployable service.

## Responsibilities

- Provide a stable public API path independent of the Python backend.
- Forward dictionary and advanced-analysis requests to FastAPI.
- Enforce request timeout and a bounded number of in-flight calls.
- Return controlled upstream errors instead of exposing backend details.
- Publish health and Prometheus metrics through Spring Boot Actuator.

This gateway does not load or host a model itself; it delegates to the Python service. Model-serving integrations can be added behind the Python service or as separate upstream adapters later.

## Endpoints

| Gateway endpoint | Python upstream |
| --- | --- |
| `GET /api/v1/words/{word}` | `GET /api/meaning/{word}` |
| `GET /api/v1/words/{word}/analysis` | `GET /api/advanced/{word}` |
| `GET /actuator/health` | Gateway health |
| `GET /actuator/prometheus` | Prometheus metrics |

## Run locally

Requirements: JDK 21 and Maven 3.9+.

From this directory:

```bash
mvn spring-boot:run
```

The gateway listens on port 8081 and expects FastAPI at `http://127.0.0.1:8000`.

Environment overrides:

- `SERVER_PORT` (default `8081`)
- `LEXIFLOW_PYTHON_BASE_URL` (default `http://127.0.0.1:8000`)
- `LEXIFLOW_GATEWAY_REQUEST_TIMEOUT` (default `5s`)
- `LEXIFLOW_GATEWAY_MAX_CONCURRENT_REQUESTS` (default `32`)

Example request:

```bash
curl http://localhost:8081/api/v1/words/serendipity
curl http://localhost:8081/api/v1/words/serendipity/analysis
```

## Validation

```bash
mvn test
mvn package
```

The gateway currently uses in-memory concurrency limiting per instance; if deploying multiple replicas, each replica enforces its own limit. Authentication, rate limiting, distributed quotas, and OpenTelemetry tracing should be added before public production exposure.

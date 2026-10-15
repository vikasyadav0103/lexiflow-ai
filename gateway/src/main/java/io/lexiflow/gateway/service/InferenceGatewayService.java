package io.lexiflow.gateway.service;

import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeoutException;

import io.lexiflow.gateway.config.GatewayProperties;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import reactor.core.publisher.Mono;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.server.ResponseStatusException;

@Service
public class InferenceGatewayService {
    private final WebClient pythonWebClient;
    private final Semaphore concurrencyLimiter;
    private final MeterRegistry meterRegistry;

    public InferenceGatewayService(
            WebClient pythonWebClient,
            GatewayProperties properties,
            MeterRegistry meterRegistry) {
        if (properties.getMaxConcurrentRequests() < 1) {
            throw new IllegalArgumentException("maxConcurrentRequests must be positive");
        }
        this.pythonWebClient = pythonWebClient;
        this.concurrencyLimiter = new Semaphore(properties.getMaxConcurrentRequests(), true);
        this.meterRegistry = meterRegistry;
    }

    public Mono<ResponseEntity<String>> lookupWord(String word) {
        return forward("/api/meaning/{word}", word, "meaning");
    }

    public Mono<ResponseEntity<String>> analyzeWord(String word) {
        return forward("/api/advanced/{word}", word, "advanced");
    }

    private Mono<ResponseEntity<String>> forward(String path, String word, String operation) {
        if (!concurrencyLimiter.tryAcquire()) {
            meterRegistry.counter("lexiflow.gateway.requests",
                    "operation", operation, "outcome", "rejected").increment();
            return Mono.error(new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "Gateway is at its concurrent request limit"));
        }

        Timer.Sample timer = Timer.start(meterRegistry);

        return pythonWebClient.get()
                .uri(path, word.trim())
                .accept(MediaType.APPLICATION_JSON)
                .exchangeToMono(response -> response.bodyToMono(String.class)
                        .defaultIfEmpty("{}")
                        .flatMap(body -> {
                            if (response.statusCode().isError()) {
                                HttpStatus status = response.statusCode().is4xxClientError()
                                        ? HttpStatus.valueOf(response.statusCode().value())
                                        : HttpStatus.BAD_GATEWAY;
                                return Mono.error(new ResponseStatusException(
                                        status, "Python inference service returned an error"));
                            }
                            return Mono.just(ResponseEntity.status(response.statusCode())
                                    .contentType(response.headers().contentType().orElse(MediaType.APPLICATION_JSON))
                                    .body(body));
                        }))
                .doOnSuccess(response -> {
                    String outcome = response != null && response.getStatusCode().is2xxSuccessful()
                            ? "success" : "upstream_error";
                    meterRegistry.counter("lexiflow.gateway.requests",
                            "operation", operation, "outcome", outcome).increment();
                })
                .doOnError(error -> meterRegistry.counter("lexiflow.gateway.requests",
                        "operation", operation, "outcome", "error").increment())
                .doFinally(signal -> {
                    timer.stop(Timer.builder("lexiflow.gateway.latency")
                            .tag("operation", operation)
                            .register(meterRegistry));
                    concurrencyLimiter.release();
                })
                .onErrorMap(error -> {
                    if (error instanceof ResponseStatusException) {
                        return error;
                    }
                    if (error instanceof TimeoutException
                            || error.getCause() instanceof TimeoutException) {
                        return new ResponseStatusException(
                                HttpStatus.GATEWAY_TIMEOUT, "Python inference service timed out", error);
                    }
                    if (error instanceof WebClientRequestException) {
                        return new ResponseStatusException(
                                HttpStatus.BAD_GATEWAY, "Python inference service is unavailable", error);
                    }
                    return new ResponseStatusException(
                            HttpStatus.BAD_GATEWAY, "Python inference service failed", error);
                });
    }
}

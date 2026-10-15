package io.lexiflow.gateway.controller;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import io.lexiflow.gateway.service.InferenceGatewayService;
import reactor.core.publisher.Mono;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
@Validated
public class InferenceController {
    private final InferenceGatewayService gatewayService;

    public InferenceController(InferenceGatewayService gatewayService) {
        this.gatewayService = gatewayService;
    }

    @GetMapping("/words/{word}")
    public Mono<ResponseEntity<String>> lookupWord(
            @PathVariable
            @Size(min = 1, max = 100)
            @Pattern(regexp = "^[\\p{L}][\\p{L}\\p{M}' -]{0,99}$")
            String word) {
        return gatewayService.lookupWord(word);
    }

    @GetMapping("/words/{word}/analysis")
    public Mono<ResponseEntity<String>> analyzeWord(
            @PathVariable
            @Size(min = 1, max = 100)
            @Pattern(regexp = "^[\\p{L}][\\p{L}\\p{M}' -]{0,99}$")
            String word) {
        return gatewayService.analyzeWord(word);
    }
}

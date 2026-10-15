package io.lexiflow.gateway.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;

import org.junit.jupiter.api.Test;

class GatewayPropertiesTest {
    @Test
    void exposesSensibleLocalDevelopmentDefaults() {
        GatewayProperties properties = new GatewayProperties();

        assertThat(properties.getPythonBaseUrl()).isEqualTo("http://127.0.0.1:8000");
        assertThat(properties.getRequestTimeout()).isEqualTo(Duration.ofSeconds(5));
        assertThat(properties.getMaxConcurrentRequests()).isEqualTo(32);
    }

    @Test
    void supportsOverridingUpstreamAndLimits() {
        GatewayProperties properties = new GatewayProperties();
        properties.setPythonBaseUrl("http://localhost:9000");
        properties.setRequestTimeout(Duration.ofSeconds(2));
        properties.setMaxConcurrentRequests(12);

        assertThat(properties.getPythonBaseUrl()).isEqualTo("http://localhost:9000");
        assertThat(properties.getRequestTimeout()).isEqualTo(Duration.ofSeconds(2));
        assertThat(properties.getMaxConcurrentRequests()).isEqualTo(12);
    }
}

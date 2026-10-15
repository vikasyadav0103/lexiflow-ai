package io.lexiflow.gateway.config;

import java.time.Duration;

import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import io.netty.handler.timeout.WriteTimeoutHandler;
import reactor.netty.http.client.HttpClient;
import reactor.netty.resources.ConnectionProvider;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class WebClientConfig {
    @Bean
    WebClient pythonWebClient(GatewayProperties properties) {
        Duration timeout = properties.getRequestTimeout();
        ConnectionProvider pool = ConnectionProvider.builder("lexiflow-python-pool")
                .maxConnections(Math.max(8, properties.getMaxConcurrentRequests()))
                .pendingAcquireMaxCount(properties.getMaxConcurrentRequests())
                .pendingAcquireTimeout(timeout)
                .build();

        HttpClient httpClient = HttpClient.create(pool)
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, Math.toIntExact(timeout.toMillis()))
                .responseTimeout(timeout)
                .doOnConnected(connection -> connection
                        .addHandlerLast(new ReadTimeoutHandler(Math.max(1, Math.toIntExact(timeout.toSeconds()))))
                        .addHandlerLast(new WriteTimeoutHandler(Math.max(1, Math.toIntExact(timeout.toSeconds())))));

        return WebClient.builder()
                .baseUrl(properties.getPythonBaseUrl())
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .build();
    }
}

package io.lexiflow.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class LexiFlowGatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(LexiFlowGatewayApplication.class, args);
    }
}

FROM quay.io/keycloak/keycloak:26.8.1 AS builder
ENV KC_DB=postgres KC_HEALTH_ENABLED=true
RUN /opt/keycloak/bin/kc.sh build
FROM quay.io/keycloak/keycloak:26.8.1
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY --chown=1000:0 themes/ /opt/keycloak/themes/
RUN chmod -R u=rwX,go=rX /opt/keycloak/themes/ia
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]

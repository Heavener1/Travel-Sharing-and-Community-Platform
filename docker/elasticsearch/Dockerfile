FROM docker.elastic.co/elasticsearch/elasticsearch:8.17.2

ENV discovery.type=single-node \
    xpack.security.enabled=false \
    xpack.security.enrollment.enabled=false \
    ES_JAVA_OPTS="-Xms512m -Xmx512m"

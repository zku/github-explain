FROM alpine:3.21

RUN apk add --no-cache git

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /data
RUN chown appuser:appgroup /data
USER appuser

ENTRYPOINT ["git"]

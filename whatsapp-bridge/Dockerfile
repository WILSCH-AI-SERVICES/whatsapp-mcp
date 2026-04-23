FROM golang:1.24-bookworm AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
COPY go.mod go.sum ./
RUN go get -u go.mau.fi/whatsmeow && go mod tidy
COPY . .
ENV CGO_ENABLED=1
RUN go build -o /out/whatsapp-bridge .

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /out/whatsapp-bridge /app/whatsapp-bridge
VOLUME ["/app/store"]
CMD ["/app/whatsapp-bridge"]

FROM golang:bookworm

RUN apt update && apt install -y  \
    golang-go \
    wget \
    dos2unix \
    && apt clean

RUN go install github.com/mailhog/MailHog@latest

ENV PATH="/root/go/bin:$PATH"

COPY commands/setup_mailhog_auth.sh /commands/setup_mailhog_auth.sh

RUN dos2unix /commands/setup_mailhog_auth.sh && chmod +x /commands/setup_mailhog_auth.sh
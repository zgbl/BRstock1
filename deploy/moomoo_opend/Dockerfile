# Use Ubuntu 18.04 as specified by the Moomoo OpenD version
FROM ubuntu:18.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for Moomoo OpenD
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl1.0.0 \
    libcurl4 \
    libxml2 \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /opend

# Copy the tar.gz file from host to container
# Note: When building, the build context must include the API/Moomoo/OpenD_Ubuntu folder
COPY API/Moomoo/OpenD_Ubuntu/moomoo_OpenD_10.4.6408_Ubuntu18.04.tar.gz /tmp/opend.tar.gz

# Extract and cleanup
RUN tar -xzf /tmp/opend.tar.gz -C /opend --strip-components=2 && \
    rm /tmp/opend.tar.gz

# Expose the API port (default 11111)
EXPOSE 11111

# Copy entrypoint script
COPY deploy/moomoo_opend/entrypoint.sh /opend/entrypoint.sh
RUN chmod +x /opend/entrypoint.sh

# Run OpenD in console mode
ENTRYPOINT ["/opend/entrypoint.sh"]
CMD ["./OpenD", "-n"]

# Shared image for every lab node: networking + security tools on Debian slim.
FROM debian:bookworm-slim
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      iproute2 iputils-ping traceroute tcpdump nmap curl dnsutils netcat-openbsd \
      iptables openssh-client openssh-server sshpass hydra sudo dnsmasq \
      python3 sqlite3 less nano vim-tiny procps ca-certificates jq file \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd
COPY node-init /usr/local/bin/node-init
RUN sed -i 's/\r$//' /usr/local/bin/node-init && chmod +x /usr/local/bin/node-init \
 && printf '%s\n' "PS1='\[\e[1;32m\]\h\[\e[0m\]:\w# '" "alias ll='ls -la'" >> /root/.bashrc
WORKDIR /root
ENTRYPOINT ["/usr/local/bin/node-init"]
CMD ["sleep", "infinity"]

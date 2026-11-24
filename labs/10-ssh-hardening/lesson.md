# Hardening an SSH server

SSH is how almost every Linux server is administered, which makes it one of the most attacked services on the internet. Lab 9 showed a password-guessing attack succeeding. This lab closes that door on a new server.

## How SSH proves identity

SSH authenticates in **both** directions.

**The server proves itself to you** with its *host key*. On first connection your client shows a fingerprint:

```
The authenticity of host '10.20.1.10' can't be established.
ED25519 key fingerprint is SHA256:Xb3k...
Are you sure you want to continue connecting (yes/no)?
```

Saying yes stores the key in `~/.ssh/known_hosts`. If the key ever changes, SSH refuses loudly, because that is what a man-in-the-middle looks like. The right way to answer "yes" the first time is to compare the fingerprint with one you got another way (from the server's console, or from an admin).

**You prove yourself to the server** with either:

- a **password**: guessable, reusable, phishable;
- a **key pair**: the private key stays on your machine, the public key goes in the server's `~/.ssh/authorized_keys`. Login proves you hold the private key without ever sending it.

## Commands

```
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub  # a host key's fingerprint
ssh-keygen -t ed25519                            # make your key pair
ssh-copy-id user@host                            # install your public key on a server
ssh user@host                                    # log in
```

Server side, in `/etc/ssh/sshd_config`:

```
PasswordAuthentication no    # keys only
PermitRootLogin no           # log in as yourself, then sudo
```

Then validate and reload without dropping existing sessions:

```
sshd -t                         # syntax check; silent means OK
kill -HUP $(cat /run/sshd.pid)  # reload (on a normal server: systemctl reload ssh)
sshd -T                         # print the effective settings
```

## Why a security person cares

- With password login off, the guessing attack from lab 9 cannot succeed no matter how many attempts are made. It is the single most effective SSH hardening step.
- Disabling root login means an attacker must also know a username, and every admin action is attributable to a person.
- Other standard steps you will meet: restricting who may log in (`AllowUsers`), limiting SSH to an admin network with a firewall (lab 7), rate limiting with tools like fail2ban, and protecting private keys with a passphrase.
- **Never lock yourself out**: keep one session open while changing SSH or firewall settings on a remote machine, and test a new login before closing it.

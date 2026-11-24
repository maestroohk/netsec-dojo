# TLS and certificates

In lab 3 you read a plain HTTP conversation straight off the wire. **TLS** (the S in HTTPS) fixes that. It gives you three things:

1. **Encryption**: someone capturing traffic sees only scrambled bytes.
2. **Integrity**: tampering with the data in transit is detected.
3. **Authentication**: you know you are talking to the real `shop.dojo.lab`, not an impostor.

Encryption without authentication is nearly worthless: an attacker in the middle could simply do TLS with you *and* with the server, reading everything in between. Authentication is what **certificates** are for.

## Certificates

A certificate is a public key plus some facts about its owner, signed by someone else:

| Field | Meaning |
|---|---|
| Subject | who the certificate is for (`CN=shop.dojo.lab`) |
| Subject Alternative Name (SAN) | the exact DNS names it is valid for. Clients check this, not the CN |
| Issuer | who signed it |
| Validity | not before / not after dates |
| Public key | used in the handshake to prove the server holds the matching private key |

## The chain of trust

Your client trusts a set of **root CAs** stored on the machine (the trust store). A server's certificate is accepted only if:

1. It chains up, signature by signature, to a root in your trust store.
2. The name you connected to is in its SAN list.
3. It is within its validity dates.

Public websites use certificates from public CAs (like Let's Encrypt) that ship in every operating system. Companies often run a **private CA** for internal sites; every company PC must be told to trust it. That is this lab.

## Tools

```
openssl s_client -connect host:443 -servername host   # do a handshake, show the chain
... </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
... | openssl x509 -noout -ext subjectAltName
curl -v https://host/                                 # shows the handshake and errors
curl -k https://host/                                 # skip verification (inspection only!)
```

On Debian/Ubuntu, add a trusted CA with:

```
cp company-ca.crt /usr/local/share/ca-certificates/
update-ca-certificates
```

## Why a security person cares

- `curl -k`, `verify=False` and "ignore certificate errors" switches in code disable the authentication part of TLS. Finding them is a common code-review finding.
- Installing a CA is powerful: whoever holds that CA's key can create a valid certificate for **any** name your machine will believe. Corporate inspection proxies and some malware both work this way. Only trust CAs you have a reason to.
- Expired or mismatched certificates train users to click through warnings, which is exactly what an attacker needs.

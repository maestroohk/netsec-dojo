# A freshly installed server with permissive SSH defaults.
set -e
# Host keys baked into the image would be shared by every lab run: make new ones.
rm -f /etc/ssh/ssh_host_*
ssh-keygen -A >/dev/null
useradd -m -s /bin/bash dev
echo "dev:$DOJO_PASS" | chpasswd
sed -i -E 's/^#?PermitRootLogin .*/PermitRootLogin yes/; s/^#?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config
grep -q '^PermitRootLogin' /etc/ssh/sshd_config || echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config
grep -q '^PasswordAuthentication' /etc/ssh/sshd_config || echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config
/usr/sbin/sshd

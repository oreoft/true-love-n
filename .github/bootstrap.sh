#!/usr/bin/env bash
set -e

# uv
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

# nvm + node
export NVM_DIR="$HOME/.nvm"
if [ ! -d "$NVM_DIR" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
fi
. "$NVM_DIR/nvm.sh"
nvm install 20
nvm alias default 20

# pm2
npm install -g pm2
pm2 startup systemd -u root --hp /root
pm2 save
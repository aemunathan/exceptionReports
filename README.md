# If not already installed:
curl -fsSL https://ollama.com/install.sh | sh

# Pull a code-oriented model:
ollama pull codellama

Adding Ollama as a startup service (recommended)
Create a user and group for Ollama:

sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama
sudo usermod -a -G ollama $(whoami)
Create a service file in /etc/systemd/system/ollama.service:

[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=$PATH"

[Install]
WantedBy=multi-user.target
Then start the service:

sudo systemctl daemon-reload
sudo systemctl enable ollama

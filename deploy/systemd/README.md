# systemd deployment

These units run the scraper once per day at 03:30 using Docker Compose.

1. Put the repository on the server, for example at `/opt/acb-scraper`.
2. If you use a different path, edit `WorkingDirectory` in `acb-scraper.service`.
3. Install the units:

```bash
sudo cp deploy/systemd/acb-scraper.service /etc/systemd/system/
sudo cp deploy/systemd/acb-scraper.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now acb-scraper.timer
```

Useful commands:

```bash
systemctl list-timers acb-scraper.timer
journalctl -u acb-scraper.service -n 200
sudo systemctl start acb-scraper.service
```

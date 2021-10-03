# hasswebhookbot
A simple maubot to get Homeassistant-notifications in your favorite matrix room


![GitHub release (latest by date)](https://img.shields.io/github/v/release/v411e/hasswebhookbot)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/v411e/hasswebhookbot/CI?label=maubot%20package%20build)

# Homeassistant Webhook Notification Bot (matrix)
A [maubot](https://github.com/maubot) bot to get Homeassistant-notifications in your favorite matrix room.

## Usage
- Load the *.mbp file into your Maubot Manager
- Create client and instance in Maubot Manager
- Configure instance `base_url`
- Invite your client into a room
- Use `!ha` or a self-defined command prefix to get setup instructions and a generated yaml snippet for the webhook setup in your homeassistant instance.

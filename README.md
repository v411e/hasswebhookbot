![GitHub release (latest by date)](https://img.shields.io/github/v/release/v411e/hasswebhookbot)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/v411e/hasswebhookbot/CI?label=maubot%20package%20build)

# Homeassistant Webhook Notification Bot for [Matrix](https://matrix.org/)
A [maubot](https://github.com/maubot) bot to get [Homeassistant](https://github.com/home-assistant)-notifications in your favorite matrix room.

## Usage
- Load the *.mbp file of the current release into your Maubot Manager
- Create client and instance in Maubot Manager
- Configure instance `base_url`
- Invite your client into a room
- Use `!ha` to get the `WEBHOOK_URL` of your room and generate a YAML snippet for the configuration of your homeassistant instance.

`configuration.yaml` on HA (don't forget to reload):
```yaml
notify:
  - name: HASS_MAUBOT
    platform: rest
    resource: "<WEBHOOK_URL>"                       # replace with your own
    method: POST_JSON
    data_template:
      message: "{'message': '{{data.message}}', 'type': '{{data.type}}', 'identifier': '{{data.identifier}}'}"
```

Send a notification from homeassistant:
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    message: Die Post ist da! 📬
    type: <message / reaction / edit>               # The type of action
    identifier: <letterbox.status / eventID.xyz>    # Use your own identifier (#1) or reference an eventID (#2)
```

Redact the last message with a given identifier:
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    type: redaction
    identifier: letterbox.status
```

The bot is stateless and can be used with multiple rooms.

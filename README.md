![GitHub release (latest by date)](https://img.shields.io/github/v/release/v411e/hasswebhookbot)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/v411e/hasswebhookbot/CI?label=maubot%20package%20build)

# Homeassistant notification bot for [matrix](https://matrix.org/) via webhooks
A [maubot](https://github.com/maubot) bot to get [Homeassistant](https://github.com/home-assistant)-notifications in your favorite matrix room.
Simple message                         |  Edited message with reaction
:-------------------------------------:|:-------------------------:
![Imgur](https://i.imgur.com/y22FQKe.jpg)|  ![Imgur](https://i.imgur.com/rPUdca3.jpeg)



## Configuration
First add this plugin to your maubot manager:
1. Load the *.mbp file of the current [release](https://github.com/v411e/hasswebhookbot/releases)
2. Create client and instance
3. Configure instance `base_url`

After setting up the plugin just invite the bot into an *encrypted* room (→ [How to enable encrypted rooms for your maubot](https://md.riess.dev/maubot)). Each room has an indvidual "webhook url". To get yours just write `!ha`. The bot replies with the `WEBHOOK_URL` of your room and also generates some YAML code for the configuration of your homeassistant instance (like below).

`configuration.yaml` on HA (don't forget to reload):
```yaml
notify:
  - name: HASS_MAUBOT
    platform: rest
    resource: "<WEBHOOK_URL>"
    method: POST_JSON
    data:
      type: "{{data.type}}"
      identifier: "{{data.identifier}}"
      callback_url: "{{data.callback_url}}"
      lifetime: "{{data.lifetime}}"
```

## Usage
The bot is stateless (no database) and can be used within multiple rooms.
```yaml
service: notify.<your_service_name>
data:
  message: <your_message>
  data:
    type: <message / reaction / edit / redaction>         # The type of action
    identifier: <letterbox.status / event_id.$DRTYGw...>  # Use your own identifier (#1) or reference an event_id (#2)
    callback_url: https://<your homeassistant instance>/api/webhook/<some_hook_id>  # Optional: Get a callback with entity_id of sent message
    lifetime: 1440    # Optional: Activate message self-deletion after given time in minutes
```

## Examples
### Send a message
```yaml
service: notify.hass_maubot
data:
  message: Die Post ist da! 📬
  data:
    type: message
    identifier: letterbox.status
    callback_url: https://ha.example.com/api/webhook/some_hook_id
    lifetime: 1440
```
### Delete a message
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    type: redaction
    identifier: letterbox.status
```
or
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    type: redaction
    identifier: event_id.$DRTYGw...     # event_id can be obtained through callback
```
### React to message
```yaml
service: notify.hass_maubot
data:
  message: 📬
  data:
    type: reaction
    identifier: letterbox.status
```
or
```yaml
service: notify.hass_maubot
data:
  message: 📬
  data:
    type: reaction
    identifier: event_id.$DRTYGw...     # event_id can be obtained through callback
```
### Edit message
```yaml
service: notify.hass_maubot
data:
  message: <del>Die Post ist da! 📬</del>
  data:
    type: edit
    identifier: letterbox.status
```
or
```yaml
service: notify.hass_maubot
data:
  message: <del>Die Post ist da! 📬</del>
  data:
    type: edit
    identifier: event_id.$DRTYGw...     # event_id can be obtained through callback
```

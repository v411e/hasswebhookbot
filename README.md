![GitHub release (latest by date)](https://img.shields.io/github/v/release/v411e/hasswebhookbot)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/v411e/hasswebhookbot/CI?label=maubot%20package%20build)

# Homeassistant notification bot for [matrix](https://matrix.org/) via webhooks
A [maubot](https://github.com/maubot) bot to get [Homeassistant](https://github.com/home-assistant)-notifications in your favorite matrix room.

## Configuration
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
    resource: "<WEBHOOK_URL>"     # replace with your own
    method: POST_JSON
    data_template:
      message: "{'message': '{{data.message}}', 'type': '{{data.type}}', 'identifier': '{{data.identifier}}', 'callback_url': '{{data.callback_url}}'}"
```

## Usage
The bot is stateless and can be used with multiple rooms.
```yaml
service: notify.<your_service_name>
data:
  message: None
  data:
    message: <your_message>
    type: <message / reaction / edit / redaction>         # The type of action
    identifier: <letterbox.status / event_id.$DRTYGw...>  # Use your own identifier (#1) or reference an event_id (#2)
    callback_url: https://<your homeassistant instance>/api/webhook/<some_hook_id>  # Optional: Get a callback with entity_id of sent message
```

## Examples
### Send a message
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    message: Die Post ist da! 📬
    type: message
    identifier: letterbox.status
    callback_url: https://ha.example.com/api/webhook/some_hook_id
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
  message: None
  data:
    message: 📬
    type: reaction
    identifier: letterbox.status
```
or
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    message: 📬
    type: reaction
    identifier: event_id.$DRTYGw...     # event_id can be obtained through callback
```
### Edit message
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    message: <del>Die Post ist da! 📬</del>
    type: edit
    identifier: letterbox.status
```
or
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    message: <del>Die Post ist da! 📬</del>
    type: edit
    identifier: event_id.$DRTYGw...     # event_id can be obtained through callback
```

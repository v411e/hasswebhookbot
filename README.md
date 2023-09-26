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

After setting up the plugin just invite the bot into an *encrypted* room. Each room has an indvidual "webhook url". To get yours just write `!ha`. The bot replies with the `WEBHOOK_URL` of your room and also generates some YAML code for the configuration of your homeassistant instance (like below).

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
      content: "{{data.content}}"
      contentType: "{{data.contentType}}"
      name: "{{data.name}}"
      thumbnailSize: 512
```

## Usage
The bot is almost stateless (database only used for lifetime) and can be used within multiple rooms.
```yaml
service: notify.<your_service_name>
data:
  message: <your_message>
  data:
    type: <message / reaction / edit / redaction / image>         # The type of action
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

### Send image
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    type: "image"
    content: "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"
    contentType: "image/png"
    name: "halogo.png"
```

**Hint:** Depending on your preference, you can choose between two different modes for the edit feature:
1. Content of `<del></del>` is discarded in the Matrix notification (`keep_del_tag: true`) <br> Notification example:
```
* - New message
```
2. Content of `<del></del>` is displayed as normal text (`keep_del_tag: false`) <br> Notification example: 
```
* Previous message - New message
```

You can change this setting on the maubot configuration page.

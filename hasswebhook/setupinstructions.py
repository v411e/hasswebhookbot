# Generate a beautiful setup instruction with individual elements
class HassWebhookSetupInstructions:
    webhook_url: str
    webhook_url_cli: str
    message_plain: str
    curl_data: str = "{\\\"message\\\": \\\"Foo bar\\\", \\\"type\\\": \\\"message\\\", \\\"identifier\\\": \\\"foo.bar\\\"}"
    message_md: str

    def __init__(self, base_url: str, bot_id: str, room_id: str):
        self.webhook_url = base_url + "_matrix/maubot/plugin/" + bot_id + "/push/" + room_id
        self.webhook_url_cli = base_url + \
            "_matrix/maubot/plugin/" + bot_id + "/push/\\" + room_id
        self.message_plain = (
            "Your Webhook-URL is: {webhook_url}".format(webhook_url=self.webhook_url))
        self.message_md = (
            """Your webhook-URL is:
{webhook_url}\n

Write this in your `configuration.yaml` on HA (don't forget to reload):
```yaml
notify:
  - name: HASS_MAUBOT
    platform: rest
    resource: \"{webhook_url}\"
    method: POST_JSON
    data:
      type: \"{data_type}\"
      identifier: \"{data_identifier}\"
      callback_url: \"{data_callback_url}\"
```
\n\n
Use this yaml to send a notification from homeassistant:
```yaml
service: notify.hass_maubot
data:
  message: Die Post ist da! 📬
  data:
    type: message / reaction / redaction / edit
    identifier: letterbox.status / eventID.xyz
    callback_url: https://<your homeassistant instance>/api/webhook/<some_hook_id>
```

Use this to redact the last message with a given identifier:
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    type: redaction
    identifier: letterbox.status
```

Use this to test the webhook via cli:
```zsh
curl -d "{curl_data}" -X POST "{webhook_url_cli}"
```
""".format(
                webhook_url=self.webhook_url,
                curl_data=self.curl_data,
                webhook_url_cli=self.webhook_url_cli,
                data_type="{{data.type}}",
                data_identifier="{{data.identifier}}",
                data_callback_url="{{data.callback_url}}"))

    def __str__(self) -> str:
        return self.message_md

    # Plain only contains the webhook-url of that specific room

    def plain(self) -> str:
        return self.message_plain

    # Markdown-formatted message also contains setup instructions

    def md(self) -> str:
        return self.message_md

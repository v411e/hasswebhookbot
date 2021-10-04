from maubot import Plugin, MessageEvent
from maubot.handlers import command, web
from mautrix.types import TextMessageEventContent, Format, MessageType, RoomID, EventID, EventType, Event, EncryptedEvent, PaginationDirection
from mautrix.errors.request import MForbidden
from mautrix.util import markdown

import json, ast
from typing import Type
from playground.hasswebhookbot.config import Config
from aiohttp.web import Request, Response


class HassWebhook(Plugin):
    config: Config


    async def start(self) -> None:
        self.config.load_and_update()


    def get_base_url(self) -> str:
        return self.config["base_url"]


    def get_command_prefix(self) -> str:
        return self.config["command_prefix"]


    @command.new(name=get_command_prefix)
    async def baseurl(self, evt: MessageEvent) -> None:
        webhook_url = self.get_base_url() + "_matrix/maubot/plugin/" + self.id + "/push/" + evt.room_id
        message_plain = ("Your Webhook-URL is: {webhook_url}".format(webhook_url = webhook_url))
        jinja_data_template = "{'message': '{{data.message}}', 'active': '{{data.active}}', 'identifier': '{{data.identifier}}'}"
        message_md = (
"""Your webhook-URL is:
{webhook_url}\n

Write this in your `configuration.yaml` on HA (don't forget to reload):
```yaml
notify:
  - name: HASS_MAUBOT
    platform: rest
    resource: \"{webhook_url}\"
    method: POST_JSON
    data_template:
      message: "{data_template_jinja}"
```
\n\n
Use this yaml to send a notification from homeassistant:
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    message: Die Post ist da! 📬
    active: True
    identifier: letterbox.status
```

Use this to redact the last message with a given identifier:
```yaml
service: notify.hass_maubot
data:
  message: None
  data:
    active: False
    identifier: letterbox.status
```
""".format(webhook_url = webhook_url, data_template_jinja=data_template_jinja))
        message_html = markdown.render(message_md, allow_html=True)
        content = TextMessageEventContent(msgtype=MessageType.TEXT, format=Format.HTML,
                                          body=message_plain, formatted_body=message_html)
        await evt.respond(content)


    @web.post("/push/{room_id}")
    async def post_data(self, req: Request) -> Response:
        room_id = req.match_info["room_id"]
        req_dict = await req.json()
        self.log.debug(req_dict)
        req_dict = ast.literal_eval(req_dict.get("message"))
        message: str = req_dict.get("message")
        active = (req_dict.get("active") == "True")
        identifier: str = req_dict.get("identifier")
        self.log.debug(f"Received data with ID {room_id}: {req_dict}")
        if (await self.send_message(room_id, message, active, identifier)):
            return Response(status=200)
        else:
            self.log.debug("I responded with 404")
            return Response(status=404)


    async def send_message (self, room_id: str, message: str, active: bool, identifier: str) -> bool:
        body = "{message} by {identifier}".format(message=message, identifier=identifier)
        content = TextMessageEventContent(msgtype=MessageType.TEXT, format=Format.HTML,
                                          body=body, formatted_body=message)
        if(active):
            # send message to room
            try:
                eventID: EventID = await self.client.send_message(room_id, content)
                self.log.debug("EventID: " + eventID)
            except MForbidden:
                self.log.error("Wrong Room ID")
                return False
            return True
        else:
            # redact last message with same identifier
            sync_result = await self.client.sync()
            prev_batch = sync_result.get("rooms").get("join").get(room_id).get("timeline").get("prev_batch")
            encrypted_eventlist = []
            get_messages_result_FW = await self.client.get_messages(
                room_id=room_id,
                direction=PaginationDirection.FORWARD,
                from_token=prev_batch,
                limit=100
                )
            encrypted_eventlist.extend(get_messages_result_FW.events)
            encrypted_eventlist = list(reversed(encrypted_eventlist))

            start = get_messages_result_FW.start
            for x in range(10):
                get_messages_result_BW = await self.client.get_messages(
                    room_id=room_id,
                    direction=PaginationDirection.BACKWARD,
                    from_token=start,
                    limit=100
                    )
                encrypted_eventlist.extend(get_messages_result_BW.events)
                start = get_messages_result_BW.end

            eventlist = []
            for encrypted_event in encrypted_eventlist:
                try:
                    event = await self.client.crypto.decrypt_megolm_event(encrypted_event)
                    if (event.sender == self.client.mxid):
                        eventlist.append(event)
                except:
                    continue

            event_id = ""
            for event in eventlist:
                content: MessageEventContent = event.content
                if body in content.body:
                    event_id = event.event_id
                    try:
                        await self.client.redact(room_id=room_id, event_id=event_id, reason="deactivated")
                    except Exception as e:
                        self.log.error(traceback.format_exc())
                    break
            return True            


    @classmethod
    def get_config_class(cls) -> Type[Config]:
        return Config

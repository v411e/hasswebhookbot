from maubot import Plugin, MessageEvent
from maubot.handlers import command, web
from mautrix.types import TextMessageEventContent, Format, MessageType, RoomID, EventID
from mautrix.errors.request import MForbidden

import json
from typing import Type
from playground.hasswebhook.config import Config
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
        await evt.reply("Your Webhook-URL is:\n\n" +
                            "```\n" + webhook_url +
                            "\n```" +
                            "\n\n" +
                            "Write this in your `configuration.yaml` on HA:\n\n" +
                            "```yaml\n" +
                            "notify:\n  - name: HASS_MAUBOT\n    platform: rest" +
                            "\n    resource: \"" + webhook_url + "\"\n    method: POST_JSON" +
                            "\n```" +
                            "\n\n" +
                            "Use this yaml to send a notification from homeassistant:\n\n" +
                            "```yaml\n" +
                            "service: notify.hass_maubot\ndata:\n  message: Die Post ist da!  📬"+
                            "\n```")


    @web.post("/push/{room_id}")
    async def post_data(self, req: Request) -> Response:
        room_id = req.match_info["room_id"]
        req_dict = await req.json()
        message = req_dict.get("message")
        self.log.debug(f"Received data with ID {room_id}: {message}")
        dictionary = {"room_id": room_id, "message": message}
        if (await self.send_message(room_id, message)):
            return Response(status=200)
        else:
            self.log.debug("I responded with 404")
            return Response(status=404)


    async def send_message (self, room_id: str, message: str) -> bool:
        content = TextMessageEventContent(msgtype=MessageType.TEXT, format=Format.HTML,
                                          body=message, formatted_body=message)
        try:
            eventID: EventID = await self.client.send_message(room_id, content)
            self.log.debug("EventID: " + eventID)
        except MForbidden:
            self.log.error("Wrong Room ID")
            return False
        return True


    @classmethod
    def get_config_class(cls) -> Type[Config]:
        return Config
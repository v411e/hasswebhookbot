from maubot import Plugin, MessageEvent
from maubot.handlers import command, web
from mautrix.types import TextMessageEventContent, Format, MessageType, RoomID, EventID, EventType, Event, EncryptedEvent, PaginationDirection
from mautrix.errors.request import MForbidden
from mautrix.util import markdown
from enum import Enum

import json, ast
from typing import Type
from .config import Config
from aiohttp.web import Request, Response
from .roomposter import RoomPoster, RoomPosterType
from .setupinstructions import HassWebhookSetupInstructions

class HassWebhook(Plugin):
    config: Config


    async def start(self) -> None:
        self.config.load_and_update()


    def get_base_url(self) -> str:
        return self.config["base_url"]


    def get_command_prefix(self) -> str:
        return self.config["command_prefix"]


    @command.new(name=get_command_prefix)
    async def setup_instructions(self, evt: MessageEvent) -> None:
        setup_instructions = HassWebhookSetupInstructions(
            base_url=self.get_base_url(),
            bot_id=self.id,
            room_id=evt.room_id
            )
        message_html = markdown.render(
            setup_instructions.md(),
            allow_html=True
            )
        content = TextMessageEventContent(
            msgtype=MessageType.TEXT,
            format=Format.HTML,
            body=setup_instructions.plain(),
            formatted_body=message_html
            )
            
        await evt.respond(content)


    @web.post("/push/{room_id}")
    async def post_data(self, req: Request) -> Response:
        room_id: str = req.match_info["room_id"]
        self.log.info(await req.text())
        req_dict = await req.json()
        self.log.debug(req_dict)
        message: str = req_dict.get("message")
        rp_type: RoomPosterType = RoomPosterType.get_type_from_str(req_dict.get("type"))
        identifier: str = req_dict.get("identifier")
        callback_url: str = req_dict.get("callback_url", "")
        room_poster: RoomPoster = RoomPoster(
            hasswebhook=self,
            message=message,
            identifier=identifier,
            rp_type=rp_type,
            room_id=room_id,
            callback_url=callback_url
            )

        self.log.debug(f"Received data with ID {room_id}: {req_dict}")
        if (await room_poster.post_to_room()):
            return Response(status=200)
        else:
            self.log.debug("I responded with 404")
            return Response(status=404)


    @classmethod
    def get_config_class(cls) -> Type[Config]:
        return Config

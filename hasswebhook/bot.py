import asyncio
import time

import pytz
from maubot import Plugin, MessageEvent
from maubot.handlers import command, web
from mautrix.types import TextMessageEventContent, Format, MessageType
from mautrix.util import markdown

from typing import Type
from .config import Config
from aiohttp.web import Request, Response
from .roomposter import RoomPoster, RoomPosterType
from .setupinstructions import HassWebhookSetupInstructions
from .db import LifetimeDatabase, LifetimeEnd
from datetime import datetime, timedelta


class HassWebhook(Plugin):
    config: Config
    db: LifetimeDatabase

    async def start(self) -> None:
        self.config.load_and_update()
        self.db = LifetimeDatabase(self.database)
        self.reminder_loop_task = asyncio.ensure_future(self.lifetime_loop(), loop=self.loop)

    async def lifetime_loop(self) -> None:
        try:
            self.log.debug("Lifetime watcher loop started")
            while True:
                now = datetime.now(tz=pytz.UTC)
                next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
                await asyncio.sleep((next_minute - now).total_seconds())
                await self.schedule_nearby_lifetime_ends(next_minute)
        except asyncio.CancelledError:
            self.log.debug("Lifetime watcher loop stopped")
        except Exception:
            self.log.exception("Exception in lifetime watcher loop")

    async def schedule_nearby_lifetime_ends(self, now: datetime) -> None:
        until = now + timedelta(minutes=1)
        for lifetime_end in self.db.get_older_than(until):
            self.log.info("ASD")
            asyncio.create_task(self.post_lifetime_end(lifetime_end))

    async def post_lifetime_end(self, lifetime_end: LifetimeEnd) -> None:
        self.db.remove(lifetime_end)
        room_poster: RoomPoster = RoomPoster(
            hasswebhook=self,
            identifier=f"event_id.{lifetime_end.event_id}",
            rp_type=RoomPosterType.REDACTION,
            room_id=lifetime_end.room_id
        )

        self.log.debug(f"Lifetime ends for event with ID {lifetime_end.event_id}.")
        await room_poster.post_to_room()

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
        rp_type: RoomPosterType = RoomPosterType.get_type_from_str(req_dict.get("type", "message"))
        identifier: str = req_dict.get("identifier", "")
        callback_url: str = req_dict.get("callback_url", "")
        lifetime: int = req_dict.get("lifetime", "")
        if lifetime == "" or int(lifetime) < 0:
            lifetime = -1
        else:
            lifetime = int(lifetime)
        self.log.info(f"Lifetime 1: {lifetime}")
        room_poster: RoomPoster = RoomPoster(
            hasswebhook=self,
            message=message,
            identifier=identifier,
            rp_type=rp_type,
            room_id=room_id,
            callback_url=callback_url,
            lifetime=lifetime
        )

        self.log.debug(f"Received data with ID {room_id}: {req_dict}")
        if await room_poster.post_to_room():
            return Response(status=200)
        else:
            self.log.debug("I responded with 404")
            return Response(status=404)

    @classmethod
    def get_config_class(cls) -> Type[Config]:
        return Config

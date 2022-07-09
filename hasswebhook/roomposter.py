import re
from base64 import b64decode
from datetime import datetime, timedelta
from enum import Enum
from io import BytesIO
from typing import Optional

import pytz
from PIL import Image as pil_image
from markdown import markdown
from maubot import Plugin
from maubot.matrix import MaubotMessageEvent
from mautrix.crypto.attachments import encrypt_attachment
from mautrix.errors.request import MForbidden
from mautrix.types import TextMessageEventContent, Format, MessageType, RoomID, PaginationDirection, \
    MessageEventContent, EventID, MediaMessageEventContent, ImageInfo, EventType, ThumbnailInfo

from .db import LifetimeEnd


class Image:
    content: str
    content_type: str
    name: str
    thumbnail_size: int

    def __init__(self, content: str, content_type: str, name: str, thumbnail_size: int = 128):
        self.content = content
        self.content_type = content_type
        self.name = name
        self.thumbnail_size = thumbnail_size


class RoomPosterType(Enum):
    MESSAGE = 1
    EDIT = 2
    REDACTION = 3
    REACTION = 4
    IMAGE = 5

    @classmethod
    def get_type_from_str(cls, mtype: str):
        type_switcher = {
            "": RoomPosterType.MESSAGE,
            "message": RoomPosterType.MESSAGE,
            "redaction": RoomPosterType.REDACTION,
            "edit": RoomPosterType.EDIT,
            "reaction": RoomPosterType.REACTION,
            "image": RoomPosterType.IMAGE
        }
        return type_switcher.get(mtype)


class RoomPoster:
    rp_type: RoomPosterType
    room_id: RoomID
    hasswebhook: Plugin
    identifier: str
    callback_url: str
    message: str
    lifetime: int

    def __init__(self, hasswebhook: Plugin, identifier: str, rp_type: RoomPosterType, room_id: str,
                 image: Optional[Image] = None, message="", callback_url="", lifetime=-1):
        self.rp_type = rp_type
        self.room_id = RoomID(room_id)
        self.hasswebhook = hasswebhook
        self.identifier = identifier
        self.callback_url = callback_url
        self.message = message
        self.lifetime = lifetime
        self.image = image

    # Send a POST as a callback containing the event_id of the sent message
    async def callback(self, event_id: str) -> None:
        if self.callback_url:
            await self.hasswebhook.http.post(self.callback_url, json={'event_id': event_id})

    # Switch for each RoomPosterType
    async def post_to_room(self):
        if self.rp_type == RoomPosterType.MESSAGE:
            return await self.post_message()
        if self.rp_type == RoomPosterType.REDACTION:
            return await self.post_redaction()
        if self.rp_type == RoomPosterType.EDIT:
            return await self.post_edit()
        if self.rp_type == RoomPosterType.REACTION:
            return await self.post_reaction()
        if self.rp_type == RoomPosterType.IMAGE:
            return await self.post_image()
        return False

    async def post_image(self) -> str:
        media_event = MediaMessageEventContent(body=self.image.name, msgtype=MessageType.IMAGE)

        upload_mime = "application/octet-stream"
        bytes_image = b64decode(self.image.content)
        encrypted_image, file = encrypt_attachment(bytes_image)
        file.url = await self.hasswebhook.client.upload_media(encrypted_image, mime_type=upload_mime)
        media_event.file = file

        img = pil_image.open(BytesIO(bytes_image))
        image_info = ImageInfo(mimetype=self.image.content_type, height=img.height, width=img.width)
        media_event.info = image_info

        byt_arr_tn = BytesIO()
        img.thumbnail((self.image.thumbnail_size, self.image.thumbnail_size), pil_image.ANTIALIAS)
        img.save(byt_arr_tn, format='PNG')

        tn_img = pil_image.open(byt_arr_tn)
        enc_tn, tn_file = encrypt_attachment(byt_arr_tn.getvalue())

        image_info.thumbnail_info = ThumbnailInfo(mimetype="image/png", height=tn_img.height, width=tn_img.width)
        tn_file.url = await self.hasswebhook.client.upload_media(enc_tn, mime_type=upload_mime)
        image_info.thumbnail_file = tn_file

        img.close()
        tn_img.close()

        event_id = await self.hasswebhook.client.send_message_event(self.room_id, event_type=EventType.ROOM_MESSAGE,
                                                                    content=media_event)
        await self.callback(event_id)
        return event_id

    # Send message to room
    async def post_message(self):
        body = "{message} by {identifier}".format(
            message=self.message, identifier=self.identifier) if self.identifier else self.message
        content = TextMessageEventContent(
            msgtype=MessageType.TEXT,
            format=Format.HTML,
            body=body,
            formatted_body=markdown(self.message)
        )
        try:
            event_id_req = await self.hasswebhook.client.send_message(self.room_id, content)
            await self.callback(event_id_req)
            # Lifetime (self-deletion)
            if self.lifetime != -1:
                end_time = datetime.now(tz=pytz.UTC) + timedelta(minutes=self.lifetime)
                self.hasswebhook.db.insert(
                    LifetimeEnd(end_date=end_time, room_id=self.room_id, event_id=event_id_req))
            return event_id_req
        except MForbidden:
            self.hasswebhook.log.error("Wrong Room ID")
            return False

    # Redact message
    async def post_redaction(self) -> bool:
        event_id = self.identifier[9:] if ("event_id." in self.identifier) else (
            await self.search_history_for_event()).event_id
        try:
            event_id_req = await self.hasswebhook.client.redact(
                room_id=self.room_id,
                event_id=event_id,
                reason="deactivated"
            )
            await self.callback(event_id_req)
        except MForbidden:
            self.hasswebhook.log.error("Wrong Room ID")
            return False
        return True

    # Edit message
    async def post_edit(self) -> bool:
        body = re.sub(r"<del>(.*)</del>", r"\1", self.message) if self.hasswebhook.get_keep_del_tag() else re.sub(
            r"<del>.*</del>", "", self.message)
        content = TextMessageEventContent(
            msgtype=MessageType.TEXT,
            format=Format.HTML,
            body=body,
            formatted_body=markdown(self.message)
        )
        event: MaubotMessageEvent = await self.search_history_for_event()
        await event.edit(content=content)
        return True

    # React on message
    async def post_reaction(self) -> bool:
        event: MaubotMessageEvent = await self.search_history_for_event()
        await event.react(key=self.message)
        return True

    # Search in room history for a message containing the identifier and return the event of that message
    async def search_history_for_event(self) -> Optional[MaubotMessageEvent]:
        if "event_id." in self.identifier:
            event_id = EventID(self.identifier[9:])
            message_event = await self.hasswebhook.client.get_event(room_id=self.room_id, event_id=event_id)
            self.hasswebhook.log.info(
                f"[search_history_for_event] event_id: {event_id}: message_event: {message_event}")
            if not message_event:
                self.hasswebhook.log.error("Could not find a matching event for event_id.")
            return message_event

        self.hasswebhook.log.debug(f"Searching for message_event... {self.identifier}")
        sync_result = await self.hasswebhook.client.sync()
        prev_batch = sync_result.get("rooms").get("join").get(
            self.room_id).get("timeline").get("prev_batch")
        encrypted_eventlist = []
        get_messages_result_FW = await self.hasswebhook.client.get_messages(
            room_id=self.room_id,
            direction=PaginationDirection.FORWARD,
            from_token=prev_batch,
            limit=100
        )
        encrypted_eventlist.extend(get_messages_result_FW.events)
        encrypted_eventlist = list(reversed(encrypted_eventlist))

        start = get_messages_result_FW.start
        for x in range(10):
            get_messages_result_BW = await self.hasswebhook.client.get_messages(
                room_id=self.room_id,
                direction=PaginationDirection.BACKWARD,
                from_token=start,
                limit=100
            )
            encrypted_eventlist.extend(get_messages_result_BW.events)
            start = get_messages_result_BW.end

        eventlist = []
        for encrypted_event in encrypted_eventlist:
            try:
                event = await self.hasswebhook.client.crypto.decrypt_megolm_event(encrypted_event)
                if event.sender == self.hasswebhook.client.mxid:
                    eventlist.append(event)
            except:
                continue

        message_event: MaubotMessageEvent = None
        for event in eventlist:
            evt_content: MessageEventContent = event.content
            if self.identifier in evt_content.body:
                message_event = MaubotMessageEvent(
                    base=event, client=self.hasswebhook.client)
                break
        if not message_event:
            self.hasswebhook.log.error("Could not find a matching event.")
            return

        self.hasswebhook.log.debug(f"Found message_event: {message_event.event_id}")
        return message_event

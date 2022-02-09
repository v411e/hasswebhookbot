from maubot import Plugin
from maubot.matrix import MaubotMessageEvent
from mautrix.types import TextMessageEventContent, Format, MessageType, RoomID, PaginationDirection, MessageEventContent
from mautrix.errors.request import MForbidden
from enum import Enum
from markdown import markdown
import re


class RoomPosterType(Enum):
    MESSAGE = 1
    EDIT = 2
    REDACTION = 3
    REACTION = 4

    def get_type_from_str(mtype: str) -> Enum:
        type_switcher = {
            "": RoomPosterType.MESSAGE,
            "message": RoomPosterType.MESSAGE,
            "redaction": RoomPosterType.REDACTION,
            "edit": RoomPosterType.EDIT,
            "reaction": RoomPosterType.REACTION
        }
        return type_switcher.get(mtype)


class RoomPoster:
    rp_type: RoomPosterType
    room_id: RoomID
    hasswebhook: Plugin
    identifier: str
    callback_url: str
    message: str

    def __init__(self, hasswebhook: Plugin, message: str, identifier: str, rp_type: RoomPosterType, room_id: str,
                 callback_url=""):
        self.rp_type = rp_type
        self.room_id = RoomID(room_id)
        self.hasswebhook = hasswebhook
        self.identifier = identifier
        self.callback_url = callback_url
        self.message = message

    # Send a POST as a callback containing the event_id of the sent message
    async def callback(self, event_id: str) -> None:
        if self.callback_url:
            await self.hasswebhook.http.post(self.callback_url, json={'event_id': event_id})

    # Switch for each RoomPosterType
    async def post_to_room(self) -> bool:
        if self.rp_type == RoomPosterType.MESSAGE:
            return await self.post_message()
        if self.rp_type == RoomPosterType.REDACTION:
            return await self.post_redaction()
        if self.rp_type == RoomPosterType.EDIT:
            return await self.post_edit()
        if self.rp_type == RoomPosterType.REACTION:
            return await self.post_reaction()
        return False

    # Send message to room

    async def post_message(self) -> bool:
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
            self.hasswebhook.log.debug("EventID: " + event_id_req)
        except MForbidden:
            self.hasswebhook.log.error("Wrong Room ID")
            return False
        return True

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
        body = re.sub(r"<del>.*<\/del>", "", self.message)
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

    async def search_history_for_event(self) -> MaubotMessageEvent:
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
        if "event_id." in self.identifier:
            event_id = self.identifier[9:]
            for event in eventlist:
                if event_id == event.event_id:
                    message_event = MaubotMessageEvent(
                        base=event, client=self.hasswebhook.client)
                    break
        else:
            for event in eventlist:
                evt_content: MessageEventContent = event.content
                if self.identifier in evt_content.body:
                    message_event = MaubotMessageEvent(
                        base=event, client=self.hasswebhook.client)
                    break
        if not message_event:
            self.hasswebhook.log.error("Could not find a matching event.")
            return message_event
        return message_event

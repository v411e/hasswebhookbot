from maubot import Plugin
from mautrix.types import TextMessageEventContent, Format, MessageType, RoomID, EventID, EventType, Event, EncryptedEvent, PaginationDirection
from mautrix.errors.request import MForbidden
from enum import Enum

from typing import Type


class RoomPosterType(Enum):
    MESSAGE = 1
    EDIT = 2
    REDACTION = 3
    REACTION = 4


    def get_type_from_str(mtype: str) -> Enum:
        typeSwitcher = {
            "message": RoomPosterType.MESSAGE,
            "redaction": RoomPosterType.REDACTION,
            "edit": RoomPosterType.EDIT,
            "reaction": RoomPosterType.REACTION
        }
        return typeSwitcher.get(mtype)


class RoomPoster:
    body: str
    content: TextMessageEventContent
    rp_type: RoomPosterType
    room_id : str
    hasswebhook : Plugin
    identifier: str
    callback_url: str


    def __init__(self, hasswebhook: Plugin, message: str, identifier: str, rp_type: RoomPosterType, room_id: str, callback_url=""):
        self.body = "{message} by {identifier}".format(message=message, identifier=identifier)
        self.content = TextMessageEventContent(
            msgtype=MessageType.TEXT,
            format=Format.HTML,
            body=self.body,
            formatted_body=message
            )
        self.rp_type = rp_type
        self.room_id = room_id
        self.hasswebhook = hasswebhook
        self.identifier = identifier
        self.callback_url = callback_url


    async def callback(self, event_id: str) -> bool:
        await self.hasswebhook.http.post(self.callback_url, json={'event_id': event_id})


    async def post_to_room (self) -> bool:
        if (self.rp_type == RoomPosterType.MESSAGE):
            return await self.post_message()
        if (self.rp_type == RoomPosterType.REDACTION):
            return await self.post_redaction()
        
        return False


    async def post_message(self) -> bool:
        # send message to room
        try:
            event_id_req = await self.hasswebhook.client.send_message(self.room_id, self.content)
            await self.callback(event_id_req)
            self.hasswebhook.log.debug("EventID: " + event_id_req)
        except MForbidden:
            self.hasswebhook.log.error("Wrong Room ID")
            return False
        return True


    async def post_redaction(self) -> bool:
        # redact last message with same identifier
        event_id = self.identifier[9:] if ("event_id." in self.identifier) else await self.search_history_for_event_id()
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


    async def post_edit(self) -> bool:
        return True


    async def post_reaction(self) -> bool:
        return True


    async def search_history_for_event_id(self) -> str:
        sync_result = await self.hasswebhook.client.sync()
        prev_batch = sync_result.get("rooms").get("join").get(self.room_id).get("timeline").get("prev_batch")
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
                if (event.sender == self.hasswebhook.client.mxid):
                    eventlist.append(event)
            except:
                continue
            
        event_id = ""
        for event in eventlist:
            evt_content: MessageEventContent = event.content
            if self.identifier in evt_content.body:
                event_id = event.event_id
                break
        return event_id
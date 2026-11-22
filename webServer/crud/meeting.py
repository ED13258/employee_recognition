from crud.base import CRUDBase
from model.meeting import Meeting
from schema.meeting import MeetingCreate, MeetingUpdate

class CRUDMeeting(CRUDBase[Meeting, MeetingCreate, MeetingUpdate]):
    def __init__(self):
        super().__init__(Meeting)
from model.meeting import Meeting
from util.datetimeConverter import datetimeConverter


def voting_started(meeting: Meeting) -> bool:
    """目前時間大於等於會議的投票開始時間，即視為投票已開始"""
    return datetimeConverter.get_current_timestamp() >= meeting.voting_kickoff


def voting_ended(meeting: Meeting) -> bool:
    """目前時間大於等於會議的截止時間，即視為投票已截止。剛好等於截止時間時也算截止"""
    return datetimeConverter.get_current_timestamp() >= meeting.voting_deadline

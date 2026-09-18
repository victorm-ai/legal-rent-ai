"""Chat routes (RF-41–RF-45)."""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.middleware.auth import require_auth
from api.schemas.delivery import (
    ChatMessageResponse,
    ChatSessionResponse,
    ChatSuggestionsResponse,
    CreateChatSessionRequest,
    SendChatMessageRequest,
)
from services.chat_service import ChatService, ChatSessionNotFoundError
from services.contract_service import ContractAccessError, ContractNotFoundError

router = APIRouter(tags=["chat"])


def _session_response(session) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=session.id,
        contract_id=session.contract_id,
        analysis_id=session.analysis_id,
        created_at=session.created_at,
    )


def _message_response(message) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        references=message.references,
        created_at=message.created_at,
    )


@router.post(
    "/contracts/{contract_id}/chat/sessions",
    response_model=ChatSessionResponse,
    status_code=201,
)
async def create_chat_session(
    contract_id: str,
    body: CreateChatSessionRequest,
    current_user: dict = Depends(require_auth),
):
    service = ChatService()
    try:
        session = service.create_session(current_user, contract_id, body.analysis_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _session_response(session)


@router.get("/contracts/{contract_id}/chat/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    service = ChatService()
    try:
        sessions = service.list_sessions(current_user, contract_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    return [_session_response(session) for session in sessions]


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: str,
    body: SendChatMessageRequest,
    current_user: dict = Depends(require_auth),
):
    service = ChatService()
    try:
        message = service.send_message(current_user, session_id, body.content)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _message_response(message)


@router.post("/chat/sessions/{session_id}/messages/stream")
async def send_chat_message_stream(
    session_id: str,
    body: SendChatMessageRequest,
    current_user: dict = Depends(require_auth),
):
    service = ChatService()

    def event_stream():
        try:
            for event in service.stream_message(current_user, session_id, body.content):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except ChatSessionNotFoundError as exc:
            payload = {"type": "error", "detail": exc.message}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except ContractAccessError as exc:
            payload = {"type": "error", "detail": exc.message}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except ValueError as exc:
            payload = {"type": "error", "detail": str(exc)}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except RuntimeError as exc:
            payload = {"type": "error", "detail": str(exc)}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def list_chat_messages(
    session_id: str,
    current_user: dict = Depends(require_auth),
):
    service = ChatService()
    try:
        messages = service.list_messages(current_user, session_id)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    return [_message_response(message) for message in messages]


@router.get("/chat/sessions/{session_id}/suggestions", response_model=ChatSuggestionsResponse)
async def get_chat_suggestions(
    session_id: str,
    current_user: dict = Depends(require_auth),
):
    service = ChatService()
    try:
        suggestions = service.get_suggestions(current_user, session_id)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    return ChatSuggestionsResponse(suggestions=suggestions)

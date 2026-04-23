"""WhatsApp MCP server entry point — read-only, allowlist-enforced.

Patched from upstream lharries/whatsapp-mcp:
  - Transport swapped from stdio to streamable-http (host/port via env).
  - Send tools (send_message, send_file, send_audio_message) stripped.
  - JID allowlist enforced via WHATSAPP_ALLOWED_JIDS env (comma-separated).
    Empty allowlist = permissive (install-time discovery mode).

Design Context:
  Allowlist applies at MCP boundary, not at WhatsApp bridge. Bridge still
  ingests all messages into SQLite — MCP is the firewall Claude sees through.
"""
import os
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    download_media as whatsapp_download_media,
)

ALLOWED_JIDS = {j.strip() for j in os.getenv("WHATSAPP_ALLOWED_JIDS", "").split(",") if j.strip()}
ALLOWLIST_ACTIVE = bool(ALLOWED_JIDS)


def _reject_if_blocked(chat_jid: Optional[str]) -> Optional[Dict[str, Any]]:
    if ALLOWLIST_ACTIVE and chat_jid and chat_jid not in ALLOWED_JIDS:
        return {"error": "chat_jid not in allowlist", "chat_jid": chat_jid}
    return None


def _jid_of(obj: Any) -> Optional[str]:
    if isinstance(obj, dict):
        return obj.get("jid") or obj.get("chat_jid")
    return getattr(obj, "jid", None) or getattr(obj, "chat_jid", None)


def _filter_chats(chats: List[Any]) -> List[Any]:
    if not ALLOWLIST_ACTIVE:
        return chats
    return [c for c in chats if _jid_of(c) in ALLOWED_JIDS]


mcp = FastMCP("whatsapp")


@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.

    Args:
        query: Search term to match against contact names or phone numbers
    """
    return whatsapp_search_contacts(query)


@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1,
) -> Any:
    """Get WhatsApp messages matching specified criteria with optional context.

    When allowlist is active and chat_jid is omitted, results are filtered
    to allowlisted chats only. Upstream returns a pre-formatted string.
    """
    blocked = _reject_if_blocked(chat_jid)
    if blocked:
        return blocked
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after,
    )
    if ALLOWLIST_ACTIVE and not chat_jid and isinstance(messages, list):
        messages = [m for m in messages if _jid_of(m) in ALLOWED_JIDS]
    return messages


@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active",
) -> List[Any]:
    """Get WhatsApp chats matching specified criteria.

    Filtered to allowlist when active. Fetches larger window then filters
    + paginates to avoid allowlist items being excluded by SQL limit.
    """
    if ALLOWLIST_ACTIVE:
        chats = whatsapp_list_chats(
            query=query,
            limit=500,
            page=0,
            include_last_message=include_last_message,
            sort_by=sort_by,
        )
        filtered = _filter_chats(chats)
        start = page * limit
        return filtered[start:start + limit]
    return whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by,
    )


@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID."""
    blocked = _reject_if_blocked(chat_jid)
    if blocked:
        return blocked
    return whatsapp_get_chat(chat_jid, include_last_message)


@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.

    Result is rejected if the matched chat is not in the allowlist.
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    if ALLOWLIST_ACTIVE and chat and _jid_of(chat) not in ALLOWED_JIDS:
        return {"error": "matched chat not in allowlist"}
    return chat


@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact. Filtered to allowlist."""
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return _filter_chats(chats)


@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.

    When allowlist is active, rejects if contact's JID is not allowlisted.
    """
    if ALLOWLIST_ACTIVE and jid not in ALLOWED_JIDS:
        return "error: jid not in allowlist"
    return whatsapp_get_last_interaction(jid)


@mcp.tool()
def get_message_context(
    message_id: str, before: int = 5, after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.

    When allowlist is active, rejects if the message's chat is not allowlisted.
    """
    context = whatsapp_get_message_context(message_id, before, after)
    if ALLOWLIST_ACTIVE:
        target = None
        if isinstance(context, dict):
            target = context.get("message")
        else:
            target = getattr(context, "message", None)
        if target and _jid_of(target) not in ALLOWED_JIDS:
            return {"error": "message's chat not in allowlist"}
    return context


@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path."""
    blocked = _reject_if_blocked(chat_jid)
    if blocked:
        return blocked
    file_path = whatsapp_download_media(message_id, chat_jid)
    if file_path:
        return {"success": True, "message": "Media downloaded successfully", "file_path": file_path}
    return {"success": False, "message": "Failed to download media"}


if __name__ == "__main__":
    host = os.getenv("WHATSAPP_MCP_HOST", "127.0.0.1")
    port = int(os.getenv("WHATSAPP_MCP_PORT", "8090"))
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport="streamable-http")

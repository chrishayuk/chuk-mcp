# chuk_mcp/protocol/messages/message_method.py
from enum import Enum


class MessageMethod(str, Enum):
    """
    Enum of available message methods in the MCP protocol.
    Updated for full MCP specification compliance.
    """

    # Core protocol methods
    PING = "ping"
    INITIALIZE = "initialize"

    # Resource methods
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"
    RESOURCES_TEMPLATES_LIST = "resources/templates/list"

    # Tool methods
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Prompt methods
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # Logging methods
    LOGGING_SET_LEVEL = "logging/setLevel"

    # Completion methods
    COMPLETION_COMPLETE = "completion/complete"

    # Sampling methods (client features)
    SAMPLING_CREATE_MESSAGE = "sampling/createMessage"

    # Roots methods (client features)
    ROOTS_LIST = "roots/list"

    # Elicitation methods (client features)
    ELICITATION_CREATE = "elicitation/create"

    # Notification methods
    NOTIFICATION_INITIALIZED = "notifications/initialized"
    NOTIFICATION_CANCELLED = "notifications/cancelled"
    NOTIFICATION_PROGRESS = "notifications/progress"
    NOTIFICATION_MESSAGE = "notifications/message"

    # Resource notifications
    NOTIFICATION_RESOURCES_LIST_CHANGED = "notifications/resources/list_changed"
    NOTIFICATION_RESOURCES_UPDATED = "notifications/resources/updated"

    # Prompt notifications
    NOTIFICATION_PROMPTS_LIST_CHANGED = "notifications/prompts/list_changed"

    # Tool notifications
    NOTIFICATION_TOOLS_LIST_CHANGED = "notifications/tools/list_changed"

    # Roots notifications
    NOTIFICATION_ROOTS_LIST_CHANGED = "notifications/roots/list_changed"

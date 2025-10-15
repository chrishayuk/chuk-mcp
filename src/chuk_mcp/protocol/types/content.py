# chuk_mcp/protocol/types/content.py
"""
Content type definitions for the Model Context Protocol.

This module defines all content types that can be used in messages,
including text, images, audio, and embedded resources.
"""

from typing import Literal, Optional, Dict, Any, List, Union
from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field

# Role types
Role = Literal["user", "assistant"]


class Annotations(McpPydanticBase):
    """
    Optional annotations for the client.

    The client can use annotations to inform how objects are used or displayed.
    """

    audience: Optional[List[Role]] = None
    """
    Describes who the intended customer of this object or data is.
    
    It can include multiple entries to indicate content useful for multiple 
    audiences (e.g., ["user", "assistant"]).
    """

    priority: Optional[float] = Field(None, ge=0.0, le=1.0)
    """
    Describes how important this data is for operating the server.
    
    A value of 1 means "most important," and indicates that the data is
    effectively required, while 0 means "least important," and indicates that
    the data is entirely optional.
    """

    model_config = {"extra": "allow"}


class TextContent(McpPydanticBase):
    """Text provided to or from an LLM."""

    type: Literal["text"] = "text"

    text: str
    """The text content of the message."""

    annotations: Optional[Annotations] = None
    """Optional annotations for the client."""

    model_config = {"extra": "allow"}


class ImageContent(McpPydanticBase):
    """An image provided to or from an LLM."""

    type: Literal["image"] = "image"

    data: str
    """The base64-encoded image data."""

    mimeType: str
    """The MIME type of the image. Different providers may support different image types."""

    annotations: Optional[Annotations] = None
    """Optional annotations for the client."""

    model_config = {"extra": "allow"}


class AudioContent(McpPydanticBase):
    """Audio provided to or from an LLM."""

    type: Literal["audio"] = "audio"

    data: str
    """The base64-encoded audio data."""

    mimeType: str
    """The MIME type of the audio. Different providers may support different audio types."""

    annotations: Optional[Annotations] = None
    """Optional annotations for the client."""

    model_config = {"extra": "allow"}


class TextResourceContents(McpPydanticBase):
    """Text contents of a specific resource or sub-resource."""

    uri: str
    """The URI of this resource."""

    mimeType: Optional[str] = None
    """The MIME type of this resource, if known."""

    text: str
    """The text of the item. This must only be set if the item can actually be represented as text (not binary data)."""

    model_config = {"extra": "allow"}


class BlobResourceContents(McpPydanticBase):
    """Binary contents of a specific resource or sub-resource."""

    uri: str
    """The URI of this resource."""

    mimeType: Optional[str] = None
    """The MIME type of this resource, if known."""

    blob: str
    """A base64-encoded string representing the binary data of the item."""

    model_config = {"extra": "allow"}


# Union type for resource contents
ResourceContents = Union[TextResourceContents, BlobResourceContents]


class EmbeddedResource(McpPydanticBase):
    """
    The contents of a resource, embedded into a prompt or tool call result.

    It is up to the client how best to render embedded resources for the benefit
    of the LLM and/or the user.
    """

    type: Literal["resource"] = "resource"

    resource: Union[TextResourceContents, BlobResourceContents]
    """The resource contents."""

    annotations: Optional[Annotations] = None
    """Optional annotations for the client."""

    model_config = {"extra": "allow"}


# Union type for all content types
Content = Union[TextContent, ImageContent, AudioContent, EmbeddedResource]


# Helper functions to create content objects


def create_text_content(
    text: str, annotations: Optional[Annotations] = None
) -> TextContent:
    """Create a text content object."""
    return TextContent(type="text", text=text, annotations=annotations)


def create_image_content(
    data: str, mime_type: str, annotations: Optional[Annotations] = None
) -> ImageContent:
    """
    Create an image content object.

    Args:
        data: Base64-encoded image data
        mime_type: MIME type of the image (e.g., "image/png", "image/jpeg")
        annotations: Optional annotations
    """
    return ImageContent(
        type="image", data=data, mimeType=mime_type, annotations=annotations
    )


def create_audio_content(
    data: str, mime_type: str, annotations: Optional[Annotations] = None
) -> AudioContent:
    """
    Create an audio content object.

    Args:
        data: Base64-encoded audio data
        mime_type: MIME type of the audio (e.g., "audio/mp3", "audio/wav")
        annotations: Optional annotations
    """
    return AudioContent(
        type="audio", data=data, mimeType=mime_type, annotations=annotations
    )


def create_embedded_resource(
    uri: str,
    content: Union[str, bytes],
    mime_type: Optional[str] = None,
    annotations: Optional[Annotations] = None,
) -> EmbeddedResource:
    """
    Create an embedded resource content object.

    Args:
        uri: URI of the resource
        content: Either text content (str) or binary content (bytes)
        mime_type: Optional MIME type
        annotations: Optional annotations
    """
    if isinstance(content, str):
        resource = TextResourceContents(uri=uri, text=content, mimeType=mime_type)
    else:
        import base64

        blob = base64.b64encode(content).decode("utf-8")
        resource = BlobResourceContents(uri=uri, blob=blob, mimeType=mime_type)  # type: ignore[assignment]

    return EmbeddedResource(type="resource", resource=resource, annotations=annotations)


def create_annotations(
    audience: Optional[List[Role]] = None, priority: Optional[float] = None
) -> Annotations:
    """
    Create an annotations object.

    Args:
        audience: List of intended audiences (e.g., ["user", "assistant"])
        priority: Priority value between 0.0 and 1.0
    """
    return Annotations(audience=audience, priority=priority)


# Utility functions for working with content


def is_text_content(content: Content) -> bool:
    """Check if content is text content."""
    return (
        isinstance(content, dict)
        and content.get("type") == "text"
        or isinstance(content, TextContent)
    )


def is_image_content(content: Content) -> bool:
    """Check if content is image content."""
    return (
        isinstance(content, dict)
        and content.get("type") == "image"
        or isinstance(content, ImageContent)
    )


def is_audio_content(content: Content) -> bool:
    """Check if content is audio content."""
    return (
        isinstance(content, dict)
        and content.get("type") == "audio"
        or isinstance(content, AudioContent)
    )


def is_embedded_resource(content: Content) -> bool:
    """Check if content is an embedded resource."""
    return (
        isinstance(content, dict)
        and content.get("type") == "resource"
        or isinstance(content, EmbeddedResource)
    )


def parse_content(data: Dict[str, Any]) -> Content:
    """
    Parse a content dictionary into the appropriate content type.

    Args:
        data: Dictionary representing content

    Returns:
        Parsed content object

    Raises:
        ValueError: If content type is unknown or invalid
    """
    content_type = data.get("type")

    if content_type == "text":
        return TextContent.model_validate(data)
    elif content_type == "image":
        return ImageContent.model_validate(data)
    elif content_type == "audio":
        return AudioContent.model_validate(data)
    elif content_type == "resource":
        return EmbeddedResource.model_validate(data)
    else:
        raise ValueError(f"Unknown content type: {content_type}")


def content_to_dict(content: Content) -> Dict[str, Any]:
    """Convert a content object to a dictionary."""
    if hasattr(content, "model_dump"):
        return content.model_dump(exclude_none=True)
    elif isinstance(content, dict):
        return content
    else:
        raise ValueError(f"Invalid content type: {type(content)}")


__all__ = [
    # Types
    "Role",
    "Annotations",
    "TextContent",
    "ImageContent",
    "AudioContent",
    "TextResourceContents",
    "BlobResourceContents",
    "ResourceContents",
    "EmbeddedResource",
    "Content",
    # Helper functions
    "create_text_content",
    "create_image_content",
    "create_audio_content",
    "create_embedded_resource",
    "create_annotations",
    # Utility functions
    "is_text_content",
    "is_image_content",
    "is_audio_content",
    "is_embedded_resource",
    "parse_content",
    "content_to_dict",
]

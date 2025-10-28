"""Tests for content types and utilities."""

import pytest
import base64
from chuk_mcp.protocol.types.content import (
    Annotations,
    TextContent,
    ImageContent,
    AudioContent,
    TextResourceContents,
    BlobResourceContents,
    EmbeddedResource,
    create_text_content,
    create_image_content,
    create_audio_content,
    create_embedded_resource,
    create_annotations,
    is_text_content,
    is_image_content,
    is_audio_content,
    is_embedded_resource,
    parse_content,
    content_to_dict,
)


class TestAnnotations:
    """Test Annotations type."""

    def test_annotations_creation(self):
        """Test creating annotations."""
        annotations = Annotations(audience=["user"], priority=0.8)
        assert annotations.audience == ["user"]
        assert annotations.priority == 0.8

    def test_annotations_optional(self):
        """Test annotations with optional fields."""
        annotations = Annotations()
        assert annotations.audience is None
        assert annotations.priority is None

    def test_annotations_priority_validation(self):
        """Test priority validation."""
        # Valid priorities
        Annotations(priority=0.0)
        Annotations(priority=0.5)
        Annotations(priority=1.0)

        # Invalid priorities
        with pytest.raises(Exception):  # Pydantic validation error
            Annotations(priority=-0.1)

        with pytest.raises(Exception):  # Pydantic validation error
            Annotations(priority=1.1)


class TestTextContent:
    """Test TextContent type."""

    def test_text_content_creation(self):
        """Test creating text content."""
        content = TextContent(type="text", text="Hello")
        assert content.type == "text"
        assert content.text == "Hello"
        assert content.annotations is None

    def test_text_content_with_annotations(self):
        """Test text content with annotations."""
        annotations = Annotations(audience=["user"], priority=0.9)
        content = TextContent(type="text", text="Hello", annotations=annotations)
        assert content.annotations == annotations


class TestImageContent:
    """Test ImageContent type."""

    def test_image_content_creation(self):
        """Test creating image content."""
        data = base64.b64encode(b"fake image").decode("utf-8")
        content = ImageContent(type="image", data=data, mimeType="image/png")
        assert content.type == "image"
        assert content.data == data
        assert content.mimeType == "image/png"

    def test_image_content_with_annotations(self):
        """Test image content with annotations."""
        data = base64.b64encode(b"fake image").decode("utf-8")
        annotations = Annotations(priority=0.5)
        content = ImageContent(
            type="image", data=data, mimeType="image/jpeg", annotations=annotations
        )
        assert content.annotations == annotations


class TestAudioContent:
    """Test AudioContent type."""

    def test_audio_content_creation(self):
        """Test creating audio content."""
        data = base64.b64encode(b"fake audio").decode("utf-8")
        content = AudioContent(type="audio", data=data, mimeType="audio/mp3")
        assert content.type == "audio"
        assert content.data == data
        assert content.mimeType == "audio/mp3"

    def test_audio_content_with_annotations(self):
        """Test audio content with annotations."""
        data = base64.b64encode(b"fake audio").decode("utf-8")
        annotations = Annotations(audience=["assistant"])
        content = AudioContent(
            type="audio", data=data, mimeType="audio/wav", annotations=annotations
        )
        assert content.annotations == annotations


class TestResourceContents:
    """Test resource contents types."""

    def test_text_resource_contents(self):
        """Test text resource contents."""
        resource = TextResourceContents(
            uri="file:///test.txt", text="Hello", mimeType="text/plain"
        )
        assert resource.uri == "file:///test.txt"
        assert resource.text == "Hello"
        assert resource.mimeType == "text/plain"

    def test_blob_resource_contents(self):
        """Test blob resource contents."""
        blob = base64.b64encode(b"binary data").decode("utf-8")
        resource = BlobResourceContents(
            uri="file:///test.bin", blob=blob, mimeType="application/octet-stream"
        )
        assert resource.uri == "file:///test.bin"
        assert resource.blob == blob
        assert resource.mimeType == "application/octet-stream"


class TestEmbeddedResource:
    """Test EmbeddedResource type."""

    def test_embedded_resource_with_text(self):
        """Test embedded resource with text contents."""
        text_resource = TextResourceContents(uri="file:///test.txt", text="Content")
        resource = EmbeddedResource(type="resource", resource=text_resource)
        assert resource.type == "resource"
        assert isinstance(resource.resource, TextResourceContents)

    def test_embedded_resource_with_blob(self):
        """Test embedded resource with blob contents."""
        blob = base64.b64encode(b"data").decode("utf-8")
        blob_resource = BlobResourceContents(uri="file:///test.bin", blob=blob)
        resource = EmbeddedResource(type="resource", resource=blob_resource)
        assert resource.type == "resource"
        assert isinstance(resource.resource, BlobResourceContents)


class TestContentHelpers:
    """Test content creation helper functions."""

    def test_create_text_content(self):
        """Test create_text_content helper."""
        content = create_text_content("Hello world")
        assert isinstance(content, TextContent)
        assert content.text == "Hello world"
        assert content.type == "text"

    def test_create_text_content_with_annotations(self):
        """Test create_text_content with annotations."""
        annotations = Annotations(priority=0.7)
        content = create_text_content("Test", annotations=annotations)
        assert content.annotations == annotations

    def test_create_image_content(self):
        """Test create_image_content helper."""
        data = base64.b64encode(b"image").decode("utf-8")
        content = create_image_content(data, "image/png")
        assert isinstance(content, ImageContent)
        assert content.data == data
        assert content.mimeType == "image/png"

    def test_create_audio_content(self):
        """Test create_audio_content helper."""
        data = base64.b64encode(b"audio").decode("utf-8")
        content = create_audio_content(data, "audio/mp3")
        assert isinstance(content, AudioContent)
        assert content.data == data
        assert content.mimeType == "audio/mp3"

    def test_create_embedded_resource_with_text(self):
        """Test create_embedded_resource with text content."""
        resource = create_embedded_resource("file:///test.txt", "Hello", "text/plain")
        assert isinstance(resource, EmbeddedResource)
        assert isinstance(resource.resource, TextResourceContents)
        assert resource.resource.text == "Hello"

    def test_create_embedded_resource_with_bytes(self):
        """Test create_embedded_resource with binary content."""
        binary_data = b"binary content"
        resource = create_embedded_resource(
            "file:///test.bin", binary_data, "application/octet-stream"
        )
        assert isinstance(resource, EmbeddedResource)
        assert isinstance(resource.resource, BlobResourceContents)
        # Verify blob is base64 encoded
        decoded = base64.b64decode(resource.resource.blob)
        assert decoded == binary_data

    def test_create_annotations(self):
        """Test create_annotations helper."""
        annotations = create_annotations(audience=["user", "assistant"], priority=0.6)
        assert annotations.audience == ["user", "assistant"]
        assert annotations.priority == 0.6


class TestContentTypeChecks:
    """Test content type checking functions."""

    def test_is_text_content_with_object(self):
        """Test is_text_content with TextContent object."""
        content = create_text_content("Test")
        assert is_text_content(content) is True

    def test_is_text_content_with_dict(self):
        """Test is_text_content with dict."""
        content_dict = {"type": "text", "text": "Test"}
        assert is_text_content(content_dict) is True  # type: ignore

    def test_is_text_content_false(self):
        """Test is_text_content returns False for non-text."""
        content = create_image_content("data", "image/png")
        assert is_text_content(content) is False

    def test_is_image_content_with_object(self):
        """Test is_image_content with ImageContent object."""
        content = create_image_content("data", "image/png")
        assert is_image_content(content) is True

    def test_is_image_content_with_dict(self):
        """Test is_image_content with dict."""
        content_dict = {"type": "image", "data": "data", "mimeType": "image/png"}
        assert is_image_content(content_dict) is True  # type: ignore

    def test_is_audio_content_with_object(self):
        """Test is_audio_content with AudioContent object."""
        content = create_audio_content("data", "audio/mp3")
        assert is_audio_content(content) is True

    def test_is_audio_content_with_dict(self):
        """Test is_audio_content with dict."""
        content_dict = {"type": "audio", "data": "data", "mimeType": "audio/mp3"}
        assert is_audio_content(content_dict) is True  # type: ignore

    def test_is_embedded_resource_with_object(self):
        """Test is_embedded_resource with EmbeddedResource object."""
        resource = create_embedded_resource("uri", "content")
        assert is_embedded_resource(resource) is True

    def test_is_embedded_resource_with_dict(self):
        """Test is_embedded_resource with dict."""
        content_dict = {"type": "resource", "resource": {}}
        assert is_embedded_resource(content_dict) is True  # type: ignore


class TestContentParsing:
    """Test content parsing functions."""

    def test_parse_text_content(self):
        """Test parsing text content."""
        data = {"type": "text", "text": "Hello"}
        content = parse_content(data)
        assert isinstance(content, TextContent)
        assert content.text == "Hello"

    def test_parse_image_content(self):
        """Test parsing image content."""
        data = {"type": "image", "data": "imagedata", "mimeType": "image/png"}
        content = parse_content(data)
        assert isinstance(content, ImageContent)
        assert content.data == "imagedata"

    def test_parse_audio_content(self):
        """Test parsing audio content."""
        data = {"type": "audio", "data": "audiodata", "mimeType": "audio/mp3"}
        content = parse_content(data)
        assert isinstance(content, AudioContent)
        assert content.data == "audiodata"

    def test_parse_embedded_resource(self):
        """Test parsing embedded resource."""
        data = {
            "type": "resource",
            "resource": {"uri": "file:///test.txt", "text": "Content"},
        }
        content = parse_content(data)
        assert isinstance(content, EmbeddedResource)

    def test_parse_unknown_content_type(self):
        """Test parsing unknown content type raises ValueError."""
        data = {"type": "unknown"}
        with pytest.raises(ValueError, match="Unknown content type"):
            parse_content(data)


class TestContentConversion:
    """Test content conversion functions."""

    def test_content_to_dict_with_object(self):
        """Test converting content object to dict."""
        content = create_text_content("Hello")
        result = content_to_dict(content)
        assert isinstance(result, dict)
        assert result["type"] == "text"
        assert result["text"] == "Hello"

    def test_content_to_dict_with_dict(self):
        """Test converting dict to dict (passthrough)."""
        content_dict = {"type": "text", "text": "Hello"}
        result = content_to_dict(content_dict)  # type: ignore
        assert result == content_dict

    def test_content_to_dict_invalid(self):
        """Test converting invalid content raises ValueError."""
        with pytest.raises(ValueError, match="Invalid content type"):
            content_to_dict("invalid")  # type: ignore


class TestContentIntegration:
    """Integration tests for content types."""

    def test_round_trip_text_content(self):
        """Test round-trip conversion of text content."""
        original = create_text_content("Test message")
        as_dict = content_to_dict(original)
        parsed = parse_content(as_dict)
        assert isinstance(parsed, TextContent)
        assert parsed.text == original.text

    def test_round_trip_image_content(self):
        """Test round-trip conversion of image content."""
        data = base64.b64encode(b"image").decode("utf-8")
        original = create_image_content(data, "image/png")
        as_dict = content_to_dict(original)
        parsed = parse_content(as_dict)
        assert isinstance(parsed, ImageContent)
        assert parsed.data == original.data

    def test_content_with_all_annotations_fields(self):
        """Test content with all annotation fields."""
        annotations = create_annotations(audience=["user", "assistant"], priority=0.85)
        content = create_text_content("Important message", annotations=annotations)

        as_dict = content_to_dict(content)
        assert "annotations" in as_dict
        assert as_dict["annotations"]["priority"] == 0.85
        assert "user" in as_dict["annotations"]["audience"]

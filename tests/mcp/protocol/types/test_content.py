#!/usr/bin/env python3
"""
Comprehensive tests for content.py module.
"""

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


class TestContentTypes:
    """Test content type classes."""

    def test_annotations(self):
        """Test Annotations creation."""
        ann = Annotations(audience=["user", "assistant"], priority=0.8)

        assert ann.audience == ["user", "assistant"]
        assert ann.priority == 0.8

    def test_text_content(self):
        """Test TextContent creation."""
        content = TextContent(text="Hello, world!")

        assert content.type == "text"
        assert content.text == "Hello, world!"

    def test_image_content(self):
        """Test ImageContent creation."""
        content = ImageContent(data="base64data", mimeType="image/png")

        assert content.type == "image"
        assert content.data == "base64data"
        assert content.mimeType == "image/png"

    def test_audio_content(self):
        """Test AudioContent creation."""
        content = AudioContent(data="base64audio", mimeType="audio/mp3")

        assert content.type == "audio"
        assert content.data == "base64audio"
        assert content.mimeType == "audio/mp3"

    def test_text_resource_contents(self):
        """Test TextResourceContents."""
        resource = TextResourceContents(uri="file:///test.txt", text="content")

        assert resource.uri == "file:///test.txt"
        assert resource.text == "content"

    def test_blob_resource_contents(self):
        """Test BlobResourceContents."""
        resource = BlobResourceContents(uri="file:///test.bin", blob="YmluYXJ5")

        assert resource.uri == "file:///test.bin"
        assert resource.blob == "YmluYXJ5"

    def test_embedded_resource(self):
        """Test EmbeddedResource."""
        text_resource = TextResourceContents(uri="file:///doc.txt", text="doc")
        embedded = EmbeddedResource(resource=text_resource)

        assert embedded.type == "resource"
        assert embedded.resource.uri == "file:///doc.txt"


class TestCreateHelpers:
    """Test create helper functions."""

    def test_create_text_content_basic(self):
        """Test create_text_content without annotations."""
        content = create_text_content("Test text")

        assert isinstance(content, TextContent)
        assert content.text == "Test text"
        assert content.type == "text"

    def test_create_text_content_with_annotations(self):
        """Test create_text_content with annotations."""
        ann = Annotations(audience=["user"], priority=1.0)
        content = create_text_content("Annotated text", annotations=ann)

        assert content.annotations == ann
        assert content.annotations.audience == ["user"]

    def test_create_image_content(self):
        """Test create_image_content."""
        image_data = base64.b64encode(b"fake image").decode("utf-8")
        content = create_image_content(image_data, "image/jpeg")

        assert isinstance(content, ImageContent)
        assert content.data == image_data
        assert content.mimeType == "image/jpeg"
        assert content.type == "image"

    def test_create_image_content_with_annotations(self):
        """Test create_image_content with annotations."""
        ann = Annotations(priority=0.5)
        content = create_image_content("imgdata", "image/png", annotations=ann)

        assert content.annotations == ann

    def test_create_audio_content(self):
        """Test create_audio_content."""
        audio_data = base64.b64encode(b"fake audio").decode("utf-8")
        content = create_audio_content(audio_data, "audio/wav")

        assert isinstance(content, AudioContent)
        assert content.data == audio_data
        assert content.mimeType == "audio/wav"
        assert content.type == "audio"

    def test_create_audio_content_with_annotations(self):
        """Test create_audio_content with annotations."""
        ann = Annotations(audience=["assistant"])
        content = create_audio_content("audiodata", "audio/mp3", annotations=ann)

        assert content.annotations == ann

    def test_create_embedded_resource_text(self):
        """Test create_embedded_resource with text content."""
        content = create_embedded_resource("file:///readme.txt", "README content")

        assert isinstance(content, EmbeddedResource)
        assert content.type == "resource"
        assert isinstance(content.resource, TextResourceContents)
        assert content.resource.uri == "file:///readme.txt"
        assert content.resource.text == "README content"

    def test_create_embedded_resource_text_with_mime(self):
        """Test create_embedded_resource with text and MIME type."""
        content = create_embedded_resource(
            "file:///data.json", '{"key": "value"}', mime_type="application/json"
        )

        assert content.resource.mimeType == "application/json"
        assert content.resource.text == '{"key": "value"}'

    def test_create_embedded_resource_binary(self):
        """Test create_embedded_resource with binary content."""
        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00"
        content = create_embedded_resource("file:///image.png", binary_data)

        assert isinstance(content, EmbeddedResource)
        assert isinstance(content.resource, BlobResourceContents)
        assert content.resource.uri == "file:///image.png"
        # Check that binary data was base64 encoded
        expected_blob = base64.b64encode(binary_data).decode("utf-8")
        assert content.resource.blob == expected_blob

    def test_create_embedded_resource_binary_with_mime(self):
        """Test create_embedded_resource with binary and MIME type."""
        binary_data = b"binary content"
        content = create_embedded_resource(
            "file:///data.bin", binary_data, mime_type="application/octet-stream"
        )

        assert content.resource.mimeType == "application/octet-stream"

    def test_create_embedded_resource_with_annotations(self):
        """Test create_embedded_resource with annotations."""
        ann = Annotations(priority=0.9)
        content = create_embedded_resource(
            "file:///important.txt", "Important", annotations=ann
        )

        assert content.annotations == ann

    def test_create_annotations_empty(self):
        """Test create_annotations with no parameters."""
        ann = create_annotations()

        assert isinstance(ann, Annotations)
        assert ann.audience is None
        assert ann.priority is None

    def test_create_annotations_with_audience(self):
        """Test create_annotations with audience."""
        ann = create_annotations(audience=["user", "assistant"])

        assert ann.audience == ["user", "assistant"]

    def test_create_annotations_with_priority(self):
        """Test create_annotations with priority."""
        ann = create_annotations(priority=0.75)

        assert ann.priority == 0.75

    def test_create_annotations_with_both(self):
        """Test create_annotations with both parameters."""
        ann = create_annotations(audience=["user"], priority=1.0)

        assert ann.audience == ["user"]
        assert ann.priority == 1.0


class TestTypeCheckers:
    """Test type checker functions."""

    def test_is_text_content_with_object(self):
        """Test is_text_content with TextContent object."""
        content = TextContent(text="Test")
        assert is_text_content(content) is True

    def test_is_text_content_with_dict(self):
        """Test is_text_content with dict."""
        content_dict = {"type": "text", "text": "Test"}
        assert is_text_content(content_dict) is True

    def test_is_text_content_with_other(self):
        """Test is_text_content with other content type."""
        content = ImageContent(data="data", mimeType="image/png")
        assert is_text_content(content) is False

    def test_is_image_content_with_object(self):
        """Test is_image_content with ImageContent object."""
        content = ImageContent(data="imgdata", mimeType="image/jpeg")
        assert is_image_content(content) is True

    def test_is_image_content_with_dict(self):
        """Test is_image_content with dict."""
        content_dict = {"type": "image", "data": "imgdata", "mimeType": "image/png"}
        assert is_image_content(content_dict) is True

    def test_is_image_content_with_other(self):
        """Test is_image_content with other content type."""
        content = TextContent(text="Not an image")
        assert is_image_content(content) is False

    def test_is_audio_content_with_object(self):
        """Test is_audio_content with AudioContent object."""
        content = AudioContent(data="audiodata", mimeType="audio/mp3")
        assert is_audio_content(content) is True

    def test_is_audio_content_with_dict(self):
        """Test is_audio_content with dict."""
        content_dict = {"type": "audio", "data": "audiodata", "mimeType": "audio/wav"}
        assert is_audio_content(content_dict) is True

    def test_is_audio_content_with_other(self):
        """Test is_audio_content with other content type."""
        content = TextContent(text="Not audio")
        assert is_audio_content(content) is False

    def test_is_embedded_resource_with_object(self):
        """Test is_embedded_resource with EmbeddedResource object."""
        resource = TextResourceContents(uri="file:///test", text="content")
        content = EmbeddedResource(resource=resource)
        assert is_embedded_resource(content) is True

    def test_is_embedded_resource_with_dict(self):
        """Test is_embedded_resource with dict."""
        content_dict = {
            "type": "resource",
            "resource": {"uri": "file:///test", "text": "content"},
        }
        assert is_embedded_resource(content_dict) is True

    def test_is_embedded_resource_with_other(self):
        """Test is_embedded_resource with other content type."""
        content = TextContent(text="Not a resource")
        assert is_embedded_resource(content) is False


class TestParseContent:
    """Test parse_content function."""

    def test_parse_text_content(self):
        """Test parsing text content."""
        data = {"type": "text", "text": "Hello"}
        content = parse_content(data)

        assert isinstance(content, TextContent)
        assert content.text == "Hello"

    def test_parse_text_content_with_annotations(self):
        """Test parsing text content with annotations."""
        data = {
            "type": "text",
            "text": "Annotated",
            "annotations": {"priority": 0.8},
        }
        content = parse_content(data)

        assert content.annotations is not None
        assert content.annotations.priority == 0.8

    def test_parse_image_content(self):
        """Test parsing image content."""
        data = {"type": "image", "data": "imgdata", "mimeType": "image/png"}
        content = parse_content(data)

        assert isinstance(content, ImageContent)
        assert content.data == "imgdata"
        assert content.mimeType == "image/png"

    def test_parse_audio_content(self):
        """Test parsing audio content."""
        data = {"type": "audio", "data": "audiodata", "mimeType": "audio/mp3"}
        content = parse_content(data)

        assert isinstance(content, AudioContent)
        assert content.data == "audiodata"
        assert content.mimeType == "audio/mp3"

    def test_parse_embedded_resource(self):
        """Test parsing embedded resource."""
        data = {
            "type": "resource",
            "resource": {"uri": "file:///test.txt", "text": "content"},
        }
        content = parse_content(data)

        assert isinstance(content, EmbeddedResource)
        assert content.resource.uri == "file:///test.txt"

    def test_parse_content_unknown_type(self):
        """Test parsing unknown content type raises error."""
        data = {"type": "unknown", "data": "something"}

        with pytest.raises(ValueError, match="Unknown content type"):
            parse_content(data)

    def test_parse_content_no_type(self):
        """Test parsing content without type."""
        data = {"text": "No type field"}

        with pytest.raises(ValueError, match="Unknown content type: None"):
            parse_content(data)


class TestContentToDict:
    """Test content_to_dict function."""

    def test_content_to_dict_text(self):
        """Test converting TextContent to dict."""
        content = TextContent(text="Test")
        result = content_to_dict(content)

        assert isinstance(result, dict)
        assert result["type"] == "text"
        assert result["text"] == "Test"

    def test_content_to_dict_with_annotations(self):
        """Test converting content with annotations to dict."""
        ann = Annotations(priority=0.5, audience=["user"])
        content = TextContent(text="Test", annotations=ann)
        result = content_to_dict(content)

        assert "annotations" in result
        assert result["annotations"]["priority"] == 0.5

    def test_content_to_dict_image(self):
        """Test converting ImageContent to dict."""
        content = ImageContent(data="imgdata", mimeType="image/jpeg")
        result = content_to_dict(content)

        assert result["type"] == "image"
        assert result["data"] == "imgdata"
        assert result["mimeType"] == "image/jpeg"

    def test_content_to_dict_audio(self):
        """Test converting AudioContent to dict."""
        content = AudioContent(data="audiodata", mimeType="audio/wav")
        result = content_to_dict(content)

        assert result["type"] == "audio"
        assert result["data"] == "audiodata"

    def test_content_to_dict_embedded_resource(self):
        """Test converting EmbeddedResource to dict."""
        resource = TextResourceContents(uri="file:///test", text="content")
        content = EmbeddedResource(resource=resource)
        result = content_to_dict(content)

        assert result["type"] == "resource"
        assert "resource" in result

    def test_content_to_dict_from_dict(self):
        """Test content_to_dict with dict input."""
        content_dict = {"type": "text", "text": "Already a dict"}
        result = content_to_dict(content_dict)

        assert result == content_dict

    def test_content_to_dict_invalid_type(self):
        """Test content_to_dict with invalid type."""
        invalid_content = "not a content object"

        with pytest.raises(ValueError, match="Invalid content type"):
            content_to_dict(invalid_content)

    def test_content_to_dict_exclude_none(self):
        """Test that None values are excluded from dict."""
        content = TextContent(text="Test")  # No annotations
        result = content_to_dict(content)

        # annotations should not be in dict if it's None
        assert "annotations" not in result or result.get("annotations") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

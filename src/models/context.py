import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from xml.dom import minidom


class ContextType(str, Enum):
    """Enum for different types of context snippets."""

    WEBSITE = "website"
    CODE = "code"
    DOCUMENT = "document"
    COMMAND = "command"
    COMMAND_RESULT = "command_result"  # For the output of bang commands
    # Add more types as needed


@dataclass
class ContextSnippet:
    """Base class for context snippets."""

    type: ContextType
    content: Dict[str, Any]

    def to_xml(self) -> str:
        """Convert the context snippet to XML format."""
        # Create root element
        root = ET.Element("context-snippet")
        root.set("type", self.type.value)

        # Add content elements
        for key, value in self.content.items():
            if value is not None:
                elem = ET.SubElement(root, key.replace("_", "-"))
                if isinstance(value, dict):
                    # Handle nested dictionaries
                    for sub_key, sub_value in value.items():
                        sub_elem = ET.SubElement(elem, sub_key.replace("_", "-"))
                        sub_elem.text = str(sub_value)
                elif isinstance(value, list):
                    # Handle lists
                    for item in value:
                        if isinstance(item, dict):
                            item_elem = ET.SubElement(elem, "item")
                            for k, v in item.items():
                                sub_elem = ET.SubElement(item_elem, k.replace("_", "-"))
                                sub_elem.text = str(v)
                        else:
                            item_elem = ET.SubElement(elem, "item")
                            item_elem.text = str(item)
                else:
                    # Simple value
                    elem.text = str(value)

        # Convert to pretty XML string
        xml_str = ET.tostring(root, encoding="unicode")
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

        # Remove XML declaration
        lines = pretty_xml.split("\n")
        if lines[0].startswith("<?xml"):
            pretty_xml = "\n".join(lines[1:])

        return pretty_xml


class ContextProvider(Protocol):
    """Protocol for context providers."""

    def get_context(self, input_data: Any) -> List[ContextSnippet]:
        """
        Get context snippets from the input data.

        Args:
            input_data: The input data to extract context from

        Returns:
            A list of context snippets
        """
        pass


@dataclass
class WebsiteContextSnippet(ContextSnippet):
    """Context snippet for website content."""

    def __init__(self, url: str, text_content: str, title: Optional[str] = None):
        content = {"url": url, "text_content": text_content, "title": title}
        super().__init__(type=ContextType.WEBSITE, content=content)


def __str__(self):
    return f"WebsiteContextSnippet(url={self.content['url']}, title={self.content['title']}, text_content={self.content['text_content'][:100]})"


@dataclass
class CommandContextSnippet(ContextSnippet):
    """Context snippet for the result of a bang command."""

    def __init__(self, command_query: str, result_text: str, source: str):
        content = {
            "command_query": command_query,
            "result_text": result_text,
            "source": source,
        }
        super().__init__(type=ContextType.COMMAND_RESULT, content=content)

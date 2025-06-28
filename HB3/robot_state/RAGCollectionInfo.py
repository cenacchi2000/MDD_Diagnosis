from typing import Optional
from dataclasses import field, dataclass

sr = system.import_library("../lib/shared_resources.py")


@dataclass
class FileInfo:
    name: str = ""
    type: Optional[str] = None
    uploaded_time: int = 0
    size: int = 0


@dataclass
class RAGCollectionInfo:
    collection_id: str = ""
    collection_name: str = ""
    description: str = ""
    files: list[FileInfo] = field(default_factory=lambda: [])


@sr.global_resource
@dataclass
class RAGCollectionInfoList:
    rag_collection: list[RAGCollectionInfo] = field(default_factory=lambda: [])
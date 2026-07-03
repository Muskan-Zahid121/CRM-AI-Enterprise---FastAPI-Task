import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.config import settings
from app.middleware.auth import get_current_user
from app.models.crm import Document
from app.models.user import User
from app.helpers.rag.document_extractor import extract_text_from_bytes
from app.helpers.rag.retriever import delete_document_chunks, index_document, rag_statistics, retrieve_similar

documents_router = APIRouter(prefix="/documents", tags=["documents"])
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])
rag_router = APIRouter(prefix="/rag", tags=["rag"])
uploads_router = APIRouter(prefix="/upload", tags=["uploads"])


class DocumentPayload(BaseModel):
    title: str
    content: str
    file_type: str = "text"
    tags: list[str] = Field(default_factory=list)


@documents_router.get("")
async def list_documents(user: User = Depends(get_current_user)):
    rows = await Document.filter(owner_id=user.id).order_by("-updated_at")
    return {"success": True, "documents": [{"id": d.id, "title": d.title, "indexed": d.indexed, "chunk_count": d.chunk_count} for d in rows]}


@documents_router.post("/upload")
async def upload_document(payload: DocumentPayload, user: User = Depends(get_current_user)):
    doc = await Document.create(owner_id=user.id, title=payload.title, content=payload.content, file_type=payload.file_type, tags=payload.tags)
    chunks = await index_document(doc, user.id)
    return {"success": True, "document": {"id": doc.id, "title": doc.title, "chunks": chunks}}


@documents_router.delete("/document")
async def delete_document(document_id: int = Query(...), user: User = Depends(get_current_user)):
    doc = await Document.filter(id=document_id, owner_id=user.id).first()
    if not doc:
        raise HTTPException(404, "Document not found.")
    await delete_document_chunks(doc.id, user.id)
    await doc.delete()
    return {"success": True}


@documents_router.post("/index")
async def index_doc(document_id: int = Query(...), user: User = Depends(get_current_user)):
    doc = await Document.filter(id=document_id, owner_id=user.id).first()
    if not doc:
        raise HTTPException(404, "Document not found.")
    chunks = await index_document(doc, user.id)
    return {"success": True, "chunks": chunks}


@documents_router.post("/chunk")
async def chunk_doc(document_id: int = Query(...), user: User = Depends(get_current_user)):
    return await index_doc(document_id, user)


@documents_router.post("/embedding")
async def embed_doc(document_id: int = Query(...), user: User = Depends(get_current_user)):
    return await index_doc(document_id, user)


@documents_router.get("/status")
async def doc_status(user: User = Depends(get_current_user)):
    return {"success": True, "stats": await rag_statistics(user.id)}


@knowledge_router.post("/upload")
async def knowledge_upload(payload: DocumentPayload, user: User = Depends(get_current_user)):
    return await upload_document(payload, user)


@knowledge_router.post("/upload-file")
async def knowledge_upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
):
    raw = await file.read()
    content, file_type = extract_text_from_bytes(raw, file.filename or "document.txt")
    doc_title = (title or file.filename or "Uploaded document").strip()
    path = await _save_bytes(raw, file.filename or "document.txt", "knowledge")
    doc = await Document.create(
        owner_id=user.id,
        title=doc_title,
        content=content,
        file_type=file_type,
        file_path=path,
    )
    chunks = await index_document(doc, user.id)
    return {
        "success": True,
        "document": {
            "id": doc.id,
            "title": doc.title,
            "chunks": chunks,
            "file_type": doc.file_type,
            "characters": len(content),
        },
    }


@knowledge_router.get("")
async def list_knowledge(user: User = Depends(get_current_user)):
    return await list_documents(user)


@knowledge_router.delete("/")
async def delete_knowledge(document_id: int = Query(...), user: User = Depends(get_current_user)):
    return await delete_document(document_id, user)


@knowledge_router.post("/search")
async def knowledge_search(q: str = Query(..., min_length=1), user: User = Depends(get_current_user)):
    results = await retrieve_similar(user.id, q, limit=8)
    return {"success": True, "query": q, "results": results}


@knowledge_router.post("/reindex")
async def reindex_all(user: User = Depends(get_current_user)):
    docs = await Document.filter(owner_id=user.id)
    total = 0
    for doc in docs:
        total += await index_document(doc, user.id)
    return {"success": True, "chunks_indexed": total}


class RagQuery(BaseModel):
    query: str = Field(min_length=1)
    limit: int = 5


@rag_router.post("/query")
async def rag_query(payload: RagQuery, user: User = Depends(get_current_user)):
    from app.helpers.llm.provider import generate_completion
    from app.helpers.prompts import RAG_SYSTEM

    chunks = await retrieve_similar(user.id, payload.query, limit=payload.limit)
    context = "\n\n".join(c["content"] for c in chunks)
    answer = await generate_completion(f"Context:\n{context}\n\nQuestion: {payload.query}\n\nAnswer using only the context.", RAG_SYSTEM)
    if answer.startswith("AI response (configure OPENAI_API_KEY") or answer.startswith("LLM error"):
        from app.helpers.agents.query_parser import format_rag_answer

        answer = format_rag_answer(payload.query, chunks)
    return {"success": True, "answer": answer, "citations": chunks}


@rag_router.post("/search")
async def rag_search(payload: RagQuery, user: User = Depends(get_current_user)):
    chunks = await retrieve_similar(user.id, payload.query, limit=payload.limit)
    return {"success": True, "results": chunks}


@rag_router.post("/retrieve")
async def rag_retrieve(payload: RagQuery, user: User = Depends(get_current_user)):
    return await rag_search(payload, user)


@rag_router.post("/answer")
async def rag_answer(payload: RagQuery, user: User = Depends(get_current_user)):
    return await rag_query(payload, user)


@rag_router.post("/rebuild-index")
async def rebuild_index(user: User = Depends(get_current_user)):
    return await reindex_all(user)


@rag_router.get("/statistics")
async def rag_stats(user: User = Depends(get_current_user)):
    return {"success": True, "stats": await rag_statistics(user.id)}


async def _save_bytes(raw: bytes, filename: str, subdir: str) -> str:
    ext = os.path.splitext(filename or "file")[1] or ".bin"
    name = f"{uuid.uuid4().hex}{ext}"
    folder = os.path.join(settings.UPLOAD_DIR, subdir)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, "wb") as f:
        f.write(raw)
    return path


async def _save_upload(file: UploadFile, subdir: str) -> str:
    content = await file.read()
    return await _save_bytes(content, file.filename or "file", subdir)


@uploads_router.post("/pdf")
async def upload_pdf(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    path = await _save_upload(file, "pdf")
    text = f"[PDF uploaded: {file.filename}] Stored at {path}. Connect PDF parser for text extraction."
    doc = await Document.create(owner_id=user.id, title=file.filename or "PDF", content=text, file_type="pdf", file_path=path)
    await index_document(doc, user.id)
    return {"success": True, "document_id": doc.id, "path": path}


@uploads_router.post("/docx")
async def upload_docx(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    path = await _save_upload(file, "docx")
    doc = await Document.create(owner_id=user.id, title=file.filename or "DOCX", content=f"[DOCX: {file.filename}]", file_type="docx", file_path=path)
    return {"success": True, "document_id": doc.id}


@uploads_router.post("/image")
async def upload_image(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    path = await _save_upload(file, "images")
    return {"success": True, "path": path}


@uploads_router.post("/audio")
async def upload_audio(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    path = await _save_upload(file, "audio")
    return {"success": True, "path": path, "message": "Connect transcription service for speech-to-text."}

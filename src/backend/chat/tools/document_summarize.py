"""Summarization tool used for uploaded documents."""

import asyncio
import logging
import re

from django.conf import settings
from django.core.files.storage import default_storage

import semchunk
from asgiref.sync import sync_to_async
from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.agents.summarize import SummarizationAgent
from chat.tools.exceptions import ModelCannotRetry
from chat.tools.utils import last_model_retry_soft_fail

logger = logging.getLogger(__name__)

HIERARCHICAL_MERGE_THRESHOLD = 8
MERGE_GROUP_SIZE = 4


@sync_to_async
def read_document_content(doc):
    """Read document content asynchronously."""
    with default_storage.open(doc.key) as f:
        return doc.file_name, f.read().decode("utf-8")


async def summarize_chunk(idx, chunk, total_chunks, doc_name, summarization_agent, ctx):
    """Summarize a single chunk of text."""
    sum_prompt = (
        f"Document: {doc_name}\n"
        "You are an agent specializing in text summarization. "
        "Generate a clear and concise summary of the following passage "
        "without answering any question in the summary "
        f"(part {idx}/{total_chunks}):\n'''\n{chunk}\n'''\n\n"
    )

    logger.debug(
        "[summarize] CHUNK %s/%s prompt=> %s", idx, total_chunks, sum_prompt[0:100] + "..."
    )

    try:
        resp = await summarization_agent.run(sum_prompt, usage=ctx.usage)
    except Exception as exc:
        logger.warning("Error during chunk summarization: %s", exc, exc_info=True)
        raise ModelRetry(
            "An error occurred while summarizing a part of the document chunk."
        ) from exc

    logger.debug("[summarize] CHUNK %s/%s response<= %s", idx, total_chunks, resp.output or "")
    return resp.output or ""


def structure_aware_chunks(text: str, chunk_size: int, overlap: float) -> list[str]:
    """Split text respecting markdown structure, then apply semchunk on oversized sections."""
    header_pattern = re.compile(r'^(#{1,3})\s+.+$', re.MULTILINE)
    sections = []
    last_end = 0
    current_header = ""

    for match in header_pattern.finditer(text):
        if last_end < match.start():
            section_text = text[last_end:match.start()].strip()
            if section_text:
                sections.append((current_header, section_text))
        current_header = match.group(0)
        last_end = match.end()

    # Last section
    remaining = text[last_end:].strip()
    if remaining:
        sections.append((current_header, remaining))

    if not sections:
        sections = [("", text)]

    # Regroup small sections, split oversized ones
    chunker = semchunk.chunkerify(
        tokenizer_or_token_counter=lambda t: len(t.split()),
        chunk_size=chunk_size,
    )

    result_chunks = []
    buffer = ""
    for header, content in sections:
        section_text = f"{header}\n{content}" if header else content
        combined = f"{buffer}\n\n{section_text}".strip() if buffer else section_text

        if len(combined.split()) <= chunk_size:
            buffer = combined
        else:
            if buffer:
                result_chunks.append(buffer)
            if len(section_text.split()) > chunk_size:
                sub_chunks = chunker(section_text, overlap=overlap)
                result_chunks.extend(sub_chunks)
                buffer = ""
            else:
                buffer = section_text

    if buffer:
        result_chunks.append(buffer)

    return result_chunks if result_chunks else [text]


async def hierarchical_merge(summaries, doc_name, instructions_hint, agent, ctx):
    """Merge summaries hierarchically for large documents."""
    if len(summaries) <= HIERARCHICAL_MERGE_THRESHOLD:
        return summaries

    # Group summaries
    groups = [summaries[i:i + MERGE_GROUP_SIZE] for i in range(0, len(summaries), MERGE_GROUP_SIZE)]

    sub_merged = []
    for group_idx, group in enumerate(groups, 1):
        sub_prompt = (
            f"Produce a coherent synthesis of these summaries "
            f"(group {group_idx}/{len(groups)} from '{doc_name}').\n\n"
            f"'''\n{'\\n\\n'.join(group)}\n'''\n\n"
            "Constraints:\n"
            "- Summarize without repetition.\n"
            "- Preserve all key information.\n"
            "Respond directly with the synthesis."
        )
        resp = await agent.run(sub_prompt, usage=ctx.usage)
        sub_merged.append(resp.output or "")

    return sub_merged


@last_model_retry_soft_fail
async def document_summarize(  # pylint: disable=too-many-locals
    ctx: RunContext, *, instructions: str | None = None
) -> ToolReturn:
    """
    Generate a complete, ready-to-use summary of the documents in context
    (do not request the documents to the user).
    Return this summary directly to the user WITHOUT any modification,
    or additional summarization.
    The summary is already optimized and MUST be presented as-is in the final response
    or translated preserving the information.

    Instructions are optional but should reflect the user's request.

    Examples:
    "Summarize this doc in 2 paragraphs" -> instructions = "summary in 2 paragraphs"
    "Summarize this doc in English" -> instructions = "In English"
    "Summarize this doc" -> instructions = "" (default)

    Args:
        instructions (str | None): The instructions the user gave to use for the summarization
    """
    try:
        instructions_hint = (
            instructions.strip() if instructions else "The summary should contain 2 or 3 parts."
        )
        summarization_agent = SummarizationAgent()

        # Collect documents content
        text_attachment = await sync_to_async(list)(
            ctx.deps.conversation.attachments.filter(
                content_type__startswith="text/",
            )
        )

        if not text_attachment:
            raise ModelCannotRetry(
                "No text documents found in the conversation. "
                "You must explain this to the user and ask them to provide documents."
            )

        documents = [await read_document_content(doc) for doc in text_attachment]

        # Chunking strategy depends on feature flag
        chunk_size = settings.SUMMARIZATION_CHUNK_SIZE
        overlap = settings.SUMMARIZATION_OVERLAP_SIZE
        use_improved = settings.FEATURE_FLAGS.improved_summarization.is_always_enabled

        if use_improved:
            documents_chunks = [
                structure_aware_chunks(doc_content, chunk_size, overlap)
                for _doc_name, doc_content in documents
            ]
        else:
            chunker = semchunk.chunkerify(
                tokenizer_or_token_counter=lambda text: len(text.split()),
                chunk_size=chunk_size,
            )
            documents_chunks = chunker(
                [doc[1] for doc in documents],
                overlap=overlap,
            )

        logger.info(
            "[summarize] chunking: %s parts (size~%s), instructions='%s'",
            sum(len(chunks) for chunks in documents_chunks),
            chunk_size,
            instructions_hint,
        )

        # Parallelize the chunk summarization with a semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(settings.SUMMARIZATION_CONCURRENT_REQUESTS)

        doc_chunk_summaries = []
        try:
            if use_improved:
                async def summarize_chunk_with_semaphore(idx, chunk, total_chunks, doc_name):
                    async with semaphore:
                        return await summarize_chunk(
                            idx, chunk, total_chunks, doc_name, summarization_agent, ctx
                        )

                for (doc_name, _doc_content), doc_chunks in zip(
                    documents, documents_chunks, strict=True
                ):
                    summarization_tasks = [
                        summarize_chunk_with_semaphore(idx, chunk, len(doc_chunks), doc_name)
                        for idx, chunk in enumerate(doc_chunks, start=1)
                    ]
                    chunk_summaries = list(await asyncio.gather(*summarization_tasks))
                    chunk_summaries = await hierarchical_merge(
                        chunk_summaries, doc_name, instructions_hint, summarization_agent, ctx
                    )
                    doc_chunk_summaries.append(chunk_summaries)
            else:
                async def summarize_chunk_legacy(idx, chunk, total_chunks):
                    async with semaphore:
                        return await summarize_chunk(
                            idx, chunk, total_chunks, "", summarization_agent, ctx
                        )

                for doc_chunks in documents_chunks:
                    summarization_tasks = [
                        summarize_chunk_legacy(idx, chunk, len(doc_chunks))
                        for idx, chunk in enumerate(doc_chunks, start=1)
                    ]
                    chunk_summaries = await asyncio.gather(*summarization_tasks)
                    doc_chunk_summaries.append(chunk_summaries)
        except ModelRetry as exc:
            logger.warning("Retryable error during chunk summarization: %s", exc, exc_info=True)
            raise
        except Exception as exc:
            logger.warning("Error during chunk summarization: %s", exc, exc_info=True)
            raise ModelRetry("An error occurred while processing document chunks.") from exc

        context = "\n\n".join(
            doc_name + "\n\n" + "\n\n".join(summaries)
            for doc_name, summaries in zip(
                (doc[0] for doc in documents),
                doc_chunk_summaries,
                strict=True,
            )
        )

        # Merge chunk summaries into a single concise summary
        merged_prompt = (
            "Produce a coherent synthesis from the summaries below.\n\n"
            f"'''\n{context}\n'''\n\n"
            "Constraints:\n"
            "- Summarize without repetition.\n"
            "- Harmonize style and terminology.\n"
            "- The final summary must be well-structured and formatted in markdown.\n"
            f"- Follow the instructions: {instructions_hint}\n"
            "Respond directly with the final summary."
        )

        logger.debug("[summarize] MERGE prompt=> %s", merged_prompt)

        try:
            merged_resp = await summarization_agent.run(merged_prompt, usage=ctx.usage)
        except Exception as exc:
            logger.warning("Error during merge summarization: %s", exc, exc_info=True)
            raise ModelRetry("An error occurred while generating the final summary.") from exc

        final_summary = (merged_resp.output or "").strip()

        if not final_summary:
            raise ModelRetry("The summarization produced an empty result.")

        logger.debug("[summarize] MERGE response<= %s", final_summary)

        return ToolReturn(
            return_value=final_summary,
            metadata={"sources": {doc[0] for doc in documents}},
        )

    except (ModelCannotRetry, ModelRetry):
        # Re-raise these as-is
        raise
    except Exception as exc:
        # Unexpected error - stop and inform user
        logger.exception("Unexpected error in document_summarize: %s", exc)
        raise ModelCannotRetry(
            f"An unexpected error occurred during document summarization: {type(exc).__name__}. "
            "You must explain this to the user and not try to answer based on your knowledge."
        ) from exc

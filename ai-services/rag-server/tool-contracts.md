# RAG Tool Contracts - Inventory Management

## refresh_corpus
- Purpose: rebuild the corpus and vector index from live inventory data
- Input: `caller` (optional)
- Output: `status`, `chunk_count`, `collection`, `corpus_path` or `error`
- Policy class: read + index update

## retrieve_context
- Purpose: retrieve relevant chunks for a query
- Input: `query` (required), `k` (optional, default 5), `caller` (optional)
- Output: `status`, `results[]` with `chunk_id`, `source_id`, `authority_tier`, `distance`, `text`
- Policy class: read

## answer_question
- Purpose: answer a question from retrieved context only, never invented figures
- Input: `query` (required), `k` (optional), `caller` (optional)
- Output: `answer`, `citations[]`, `confidence_category`, `retrieval_summary` or `error`
- Policy class: read + grounded response

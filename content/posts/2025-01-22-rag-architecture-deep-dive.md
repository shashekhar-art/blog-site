---
title: "RAG Architecture Deep Dive: Building Production-Ready Retrieval Systems"
date: "2025-01-22"
category: "RAG"
tags: ["RAG", "VectorSearch", "LangChain", "Production", "Python"]
summary: "Retrieval-Augmented Generation is the backbone of enterprise AI. This deep dive covers everything from basic RAG to advanced patterns like hybrid search, HyDE, and re-ranking."
cover_gradient: "gradient-3"
cover_emoji: "🔍"
author: "Shashi Shekhar"
---

## Why RAG Exists

Frontier LLMs know a lot. They've been trained on a significant chunk of the internet. But they don't know **your** data — your product documentation, your internal policies, your customer conversations, your proprietary research.

Fine-tuning can help, but it's expensive, slow, and doesn't update in real-time. **Retrieval-Augmented Generation (RAG)** solves this elegantly: at query time, pull the relevant context from your knowledge base and include it in the prompt.

The core idea is simple. The implementation details are where it gets interesting.

## The Basic RAG Pipeline

```
User Query
    │
    ▼
[Embedding Model] → Query Vector
    │
    ▼
[Vector Store] → Top-K Relevant Chunks
    │
    ▼
[LLM] ← (Query + Chunks as context)
    │
    ▼
Response
```

Here's the minimal implementation:

```python
import anthropic
from sentence_transformers import SentenceTransformer
import chromadb

# Initialize
client = anthropic.Anthropic()
embed_model = SentenceTransformer('all-MiniLM-L6-v2')
chroma = chromadb.Client()
collection = chroma.create_collection("docs")

def index_documents(docs: list[str]):
    embeddings = embed_model.encode(docs).tolist()
    ids = [f"doc_{i}" for i in range(len(docs))]
    collection.add(embeddings=embeddings, documents=docs, ids=ids)

def rag_query(question: str, top_k: int = 5) -> str:
    # Retrieve
    query_embedding = embed_model.encode([question]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=top_k)
    context = "\n\n".join(results["documents"][0])

    # Generate
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Answer based on the context below. If unsure, say so.

Context:
{context}

Question: {question}"""
        }]
    )
    return response.content[0].text
```

This works. But naive RAG fails in production in predictable ways. Let me walk through the failure modes and how to fix them.

## Failure Mode 1: Chunking Strategy

The most underestimated factor in RAG quality. Bad chunking destroys retrieval.

**Fixed-size chunking (naive)**:
```python
# BAD: cuts mid-sentence, mid-concept
def naive_chunk(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]
```

**Semantic chunking (better)**:
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)

# Respects sentence and paragraph boundaries
chunks = splitter.split_text(document)
```

**Hierarchical chunking (best for complex docs)**:

Index the same content at multiple granularities. Retrieve small chunks for precision, but send the parent context to the LLM:

```python
# Parent chunk: 2000 tokens (for context)
# Child chunk: 400 tokens (for retrieval)

from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore

docstore = InMemoryStore()
retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=docstore,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)
```

## Failure Mode 2: Embedding Model Choice

Not all embedding models are equal. The right choice depends on your domain:

| Model | Dimensions | Best For | Speed |
|-------|-----------|----------|-------|
| text-embedding-3-small | 1536 | General English | Fast |
| text-embedding-3-large | 3072 | High precision | Medium |
| all-MiniLM-L6-v2 | 384 | Local deployment | Very Fast |
| e5-large | 1024 | Multilingual | Medium |
| domain-specific fine-tuned | varies | Your domain | Varies |

For enterprise, I usually recommend starting with `text-embedding-3-small` and upgrading to a domain-fine-tuned model once you have enough labeled data.

## Failure Mode 3: Simple Cosine Similarity Misses Keyword Matches

Pure semantic search misses exact keyword matches. Pure keyword search misses semantic variants. The solution: **hybrid search**.

```python
from langchain.retrievers import EnsembleRetriever, BM25Retriever

# Semantic (dense) retrieval
dense_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

# Keyword (sparse) retrieval - BM25
bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 10

# Combine with weights
hybrid_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, dense_retriever],
    weights=[0.4, 0.6],  # Tune these based on your data
)
```

In my experience, hybrid retrieval improves answer quality by 15-25% on typical enterprise datasets.

## Advanced Pattern: HyDE (Hypothetical Document Embeddings)

The query "What's the refund policy?" and the actual policy document don't look similar in embedding space. HyDE solves this by having the LLM generate a hypothetical answer first, then using that as the query embedding.

```python
def hyde_query(question: str) -> str:
    # Step 1: Generate hypothetical answer
    hyp_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"Write a brief answer to: {question}"
        }]
    )
    hypothetical_doc = hyp_response.content[0].text

    # Step 2: Embed the hypothetical doc (not the original query)
    hyp_embedding = embed_model.encode([hypothetical_doc]).tolist()

    # Step 3: Retrieve using hypothetical embedding
    results = collection.query(query_embeddings=hyp_embedding, n_results=5)
    return results
```

## Advanced Pattern: Re-Ranking

Retrieval gets you candidates. Re-ranking gets you the *right* candidates.

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def retrieve_and_rerank(query: str, top_n: int = 5) -> list[str]:
    # Get more candidates than you need
    candidates = retriever.get_relevant_documents(query, k=20)

    # Re-rank with cross-encoder
    pairs = [(query, doc.page_content) for doc in candidates]
    scores = reranker.predict(pairs)

    # Sort by re-rank score
    ranked = sorted(zip(scores, candidates), reverse=True)
    return [doc.page_content for _, doc in ranked[:top_n]]
```

Cross-encoders are slower (they process query-document pairs), but they're dramatically more accurate than bi-encoder similarity alone.

## Evaluation: Measuring RAG Quality

The most neglected part of RAG pipelines. How do you know it's actually working?

```python
from ragas import evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
)

# Prepare test dataset
from datasets import Dataset

test_data = {
    "question": ["What is the refund policy?", ...],
    "answer": [rag_chain.invoke(q) for q in questions],
    "contexts": [retrieve(q) for q in questions],
    "ground_truth": ["Refunds within 30 days...", ...],
}

dataset = Dataset.from_dict(test_data)
result = evaluate(dataset, metrics=[
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
])
print(result)
```

Key metrics to track:
- **Faithfulness**: Is the answer grounded in the retrieved context?
- **Answer Relevancy**: Does the answer actually address the question?
- **Context Recall**: Did retrieval find the relevant documents?
- **Context Precision**: Were the retrieved documents actually relevant?

## Production Checklist

Before going live with a RAG system, ensure you have:

- [ ] Chunking strategy validated on your specific document types
- [ ] Hybrid retrieval (dense + sparse)
- [ ] Re-ranking step for high-stakes queries
- [ ] Evaluation suite with 50+ annotated Q&A pairs
- [ ] Logging of queries, retrieved contexts, and responses
- [ ] Monitoring for retrieval failures and low-confidence responses
- [ ] A "no context" fallback when retrieval fails
- [ ] User feedback mechanism to collect corrections

## Conclusion

RAG transforms LLMs from general-knowledge tools into systems that reason over your specific data. The basic implementation is surprisingly simple. Production-quality RAG — with good chunking, hybrid retrieval, re-ranking, and evaluation — takes more work, but delivers dramatically better results.

In my experience implementing RAG systems for enterprise clients, the teams that invest in evaluation infrastructure consistently outperform those chasing the latest model or architecture. The data flywheel matters more than the algorithm.

Start simple. Measure everything. Iterate.

---

*Next in this series: Building AI agents with tool use. Follow along on [LinkedIn](https://www.linkedin.com/in/shashi-shekhar-18octo/).*

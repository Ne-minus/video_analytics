from storage.app.core.config import settings

INDEX_NAME = "media_documents"

INDEX_SETTINGS = {
    "index": {
        "number_of_shards": 1,
        "number_of_replicas": settings.ES_REPLICAS,
        "refresh_interval": "1s",
        "max_result_window": 10_000,
    },
    "analysis": {
        "filter": {
            "russian_stop": {
                "type": "stop",
                "stopwords": "_russian_"
            },
            "russian_stemmer": {
                "type": "stemmer",
                "language": "russian"
            }
        },
        "analyzer": {
            "custom_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "russian_stop", "russian_stemmer"]
            }
        }
    }
}

MAPPINGS = {
    "properties": {
        "document_id": {"type": "keyword"},
        "description": {
            "type": "text",
            "analyzer": "custom_analyzer"
        },
        "dense_vector": {
            "type": "dense_vector",
            "dims": settings.ES_VECTOR_DIMS,
            "similarity": "cosine"
        },
        "created_at": {"type": "date"},
        "updated_at": {"type": "date"}
    }
}
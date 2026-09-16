import os
os.environ['USE_TF'] = '0'
os.environ['TRANSFORMERS_NO_TF'] = '1'
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

embedder = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
db = Chroma(collection_name='automotive_diagnostics', persist_directory='backend/data/vector_store', embedding_function=embedder)
try:
    res = db._collection.get(where={'record_id': {'$contains': 'P0011'}})
    print('Found', len(res['ids']))
except Exception as e:
    print('Error:', e)

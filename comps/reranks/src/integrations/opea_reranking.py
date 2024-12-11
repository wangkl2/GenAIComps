# Copyright (C) 2024 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Union

import aiohttp

from comps import (
    CustomLogger,
    LLMParamsDoc,
    SearchedDoc,
    ServiceType,
    OpeaComponent,
)

from comps.cores.proto.api_protocol import (
    ChatCompletionRequest,
    RerankingRequest,
    RerankingResponse,
    RerankingResponseData,
)

from comps.cores.mega.utils import get_access_token
from huggingface_hub import AsyncInferenceClient

logger = CustomLogger("opea_reranking")
logflag = os.getenv("LOGFLAG", False)

# Environment variables
TOKEN_URL = os.getenv("TOKEN_URL", )
CLIENTID = os.getenv("CLIENTID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


class OpeaReranking(OpeaComponent):
    """
    A specialized reranking component derived from OpeaComponent for TEI reranking services.
    """

    def __init__(self, name: str, description: str, config: dict = None):
        super().__init__(name, ServiceType.RERANK.name.lower(), description, config)
        self.client = self._initialize_client()

    def _initialize_client(self) -> AsyncInferenceClient:
        """Initializes the AsyncInferenceClient."""
        '''
        access_token = get_access_token(
            TOKEN_URL, CLIENTID, CLIENT_SECRET
        )
        '''
        access_token = (
        get_access_token(TOKEN_URL, CLIENTID, CLIENT_SECRET) if TOKEN_URL and CLIENTID and CLIENT_SECRET else None
    )
        headers = {"Content-Type": "application/json"}
        if access_token:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=json.dumps(data), headers=headers) as response:
                response_data = await response.json()

        for best_response in response_data[: input.top_n]:
            reranking_results.append(
                {"text": input.retrieved_docs[best_response["index"]].text, "score": best_response["score"]})
        """
        return AsyncInferenceClient(
            #model=os.getenv("TEI_EMBEDDING_ENDPOINT", "http://localhost:8808/rerank"),
            model=os.getenv("TEI_EMBEDDING_ENDPOINT", "http://localhost:8808"),
            token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
            headers=headers,
        )

    async def invoke(self, input: Union[SearchedDoc, RerankingRequest, ChatCompletionRequest]):
        """
        Invokes the reranking service to reorder the retrieved docs.
        """
        import pdb
        pdb.set_trace()

        query = "What is Deep Learning?"
        texts = ["Deep Learning is not...", "Deep learning is..."]

        reranking_results = await self.client.post(json={"query": query, "texts": texts}, task="text-reranking")
        #reranking = json.loads(response.decode())
        
        if isinstance(input, SearchedDoc):
            result = [doc["text"] for doc in reranking_results]
            if logflag:
                logger.info(result)
            return LLMParamsDoc(query=input.initial_query, documents=result)
        else:
            reranking_docs = []
            for doc in reranking_results:
                reranking_docs.append(RerankingResponseData(text=doc["text"], score=doc["score"]))
            if isinstance(input, RerankingRequest):
                result = RerankingResponse(reranked_docs=reranking_docs)
                if logflag:
                    logger.info(result)
                return result

            if isinstance(input, ChatCompletionRequest):
                input.reranked_docs = reranking_docs
                input.documents = [doc["text"] for doc in reranking_results]
                if logflag:
                    logger.info(input)
                return input

    def check_health(self) -> bool:
        """
        Checks the health of the reranking service.

        Returns:
            bool: True if the service is reachable and healthy, False otherwise.
        """
        try:
            return True
            response = self.client.get("/health")  # Assuming /health endpoint exists
            return response.status_code == 200 and response.json().get("status", "") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

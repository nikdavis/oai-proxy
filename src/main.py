import os

import httpx
import logfire
import loguru
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.hydrator import ChatHydrator, clients

load_dotenv()


app = FastAPI()

# setup logging & instrumentation
logfire.configure()
logfire.instrument_fastapi(app)

logger = loguru.logger
logger.configure(handlers=[logfire.loguru_handler()])

# setup env vars
LLM_BASE_URL = os.getenv("LLM_BASE_URL")


@app.middleware("http")
async def proxy_middleware(request: Request, call_next):
    hydrator = ChatHydrator(clients)

    try:
        # Log incoming request
        logger.info(f"Request: {request.url}")
        logger.info(f"Proxying to: {LLM_BASE_URL}{request.url.path}")

        logger.info(f"0) request.url.path: {request.url.path}")
        # Special handling for chat completions
        should_modify_request = request.url.path.endswith("/chat/completions")
        # should_modify_request = False
        logger.info(f"1) Should modify request: {should_modify_request}")
        # Read the request body
        body = None
        if request.method != "GET":
            logger.info("2) method != GET")
            try:
                body = await request.json()
                # Modify content for chat completions
                if should_modify_request:
                    logger.info("3) should_modify_request")
                    # Handle case where body is a list of messages directly
                    # if isinstance(body, list):
                    #     print("4) body is a list")
                    #     logger.info("Request body is a list, converting to standard format")
                    #     messages = body
                    #     body = {"messages": messages}
                    # else:
                    #     print("5) body is not a list")
                    #     messages = body.get("messages", [])

                    logger.info("6) hydrating body")
                    # Hydrate the chat by finding URLs and extracting context
                    hydrated_body = await hydrator.get_hydrated_chat(body)
                    body = hydrated_body
                    logger.info("Chat has been hydrated with context")
            except Exception as e:
                logger.exception("Error hydrating body")
                # For non-JSON bodies, read as bytes
                body = await request.body()

        # Prepare headers for the forwarded request
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        # Forward the request to the target server
        async with httpx.AsyncClient() as client:
            # Build the request
            target_url = f"{LLM_BASE_URL}{request.url.path}"
            if request.url.query:
                target_url += f"?{request.url.query}"

            # Make the request with appropriate method and data
            if request.method == "GET":
                response = await client.get(target_url, headers=headers, timeout=120.0)
            else:
                # JSON body if it's already parsed, otherwise raw bytes
                kwargs = {}
                if isinstance(body, (dict, list)):
                    kwargs["json"] = body
                else:
                    kwargs["content"] = body

                response = await client.request(
                    request.method, target_url, headers=headers, timeout=120.0, **kwargs
                )

            logger.info(f"Received response with status {response.status_code}")

            # Prepare headers for the final response, removing encodings httpx handles
            final_response_headers = dict(response.headers)
            final_response_headers.pop("content-encoding", None)
            final_response_headers.pop("content-length", None)
            final_response_headers.pop("transfer-encoding", None)

            # Return the response
            return StreamingResponse(
                content=augment_response(response.aiter_bytes(), should_modify_request),
                status_code=response.status_code,
                headers=final_response_headers,
            )

    except httpx.RequestError as e:
        error_message = str(e)
        logger.error(f"Error forwarding request: {error_message}")
        return JSONResponse(
            content={
                "error": {
                    "message": f"Error connecting to OpenAI: {error_message}",
                    "type": "proxy_error",
                }
            },
            status_code=502,
        )
    except Exception as e:
        logger.exception(f"Unexpected error in middleware: {str(e)}")
        return JSONResponse(
            content={
                "error": {"message": f"Proxy error: {str(e)}", "type": "proxy_error"}
            },
            status_code=500,
        )


async def augment_response(response_stream, should_modify=False):
    async for chunk in response_stream:
        # Only modify if it's a chat completion response and modification is enabled
        if should_modify:
            # You can add your response modification logic here if needed
            pass
        yield chunk


if __name__ == "__main__":
    logger.info(f"Starting proxy server, forwarding to {LLM_BASE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=9000)

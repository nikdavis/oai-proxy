from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import uvicorn
import logging
from src.hydrator import hydrator
from src.clients.website_client import WebsiteContextClient


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
OPENAI_URL = "http://daddy-penguin:30001"


@app.middleware("http")
async def proxy_middleware(request: Request, call_next):
    try:
        # Log incoming request
        logger.info(f"Received {request.method} request to {request.url.path}")
        logger.info(f"Proxying to {OPENAI_URL}{request.url.path}")

        # Special handling for chat completions
        should_modify_request = request.url.path.endswith("/v1/chat/completions")

        # Read the request body
        body = None
        if request.method != "GET":
            try:
                body = await request.json()

                # Modify content for chat completions
                if should_modify_request:
                    # Handle case where body is a list of messages directly
                    if isinstance(body, list):
                        logger.info("Request body is a list, converting to standard format")
                        messages = body
                        body = {"messages": messages}
                    else:
                        messages = body.get("messages", [])

                    # Hydrate the chat by finding URLs and extracting context
                    hydrated_body = await hydrator.get_hydrated_chat(body)
                    body = hydrated_body
                    logger.info("Chat has been hydrated with context")
            except:
                # For non-JSON bodies, read as bytes
                body = await request.body()

        # Prepare headers for the forwarded request
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        # Forward the request to the target server
        async with httpx.AsyncClient() as client:
            # Build the request
            target_url = f"{OPENAI_URL}{request.url.path}"
            if request.url.query:
                target_url += f"?{request.url.query}"

            # Make the request with appropriate method and data
            if request.method == "GET":
                response = await client.get(
                    target_url,
                    headers=headers,
                    timeout=120.0
                )
            else:
                # JSON body if it's already parsed, otherwise raw bytes
                kwargs = {}
                if isinstance(body, (dict, list)):
                    kwargs["json"] = body
                else:
                    kwargs["content"] = body

                response = await client.request(
                    request.method,
                    target_url,
                    headers=headers,
                    timeout=120.0,
                    **kwargs
                )

            logger.info(f"Received response with status {response.status_code}")

            # Return the response
            return StreamingResponse(
                content=augment_response(response.aiter_bytes(), should_modify_request),
                status_code=response.status_code,
                headers=dict(response.headers)
            )

    except httpx.RequestError as e:
        error_message = str(e)
        logger.error(f"Error forwarding request: {error_message}")
        return JSONResponse(
            content={"error": {"message": f"Error connecting to OpenAI: {error_message}", "type": "proxy_error"}},
            status_code=502
        )
    except Exception as e:
        logger.exception(f"Unexpected error in middleware: {str(e)}")
        return JSONResponse(
            content={"error": {"message": f"Proxy error: {str(e)}", "type": "proxy_error"}},
            status_code=500
        )

async def augment_response(response_stream, should_modify=False):
    async for chunk in response_stream:
        # Only modify if it's a chat completion response and modification is enabled
        if should_modify:
            # You can add your response modification logic here if needed
            pass
        yield chunk


if __name__ == "__main__":
    logger.info(f"Starting proxy server, forwarding to {OPENAI_URL}")
    uvicorn.run(app, host="0.0.0.0", port=9000)

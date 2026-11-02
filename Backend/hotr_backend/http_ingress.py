"""Bound HTTP reception before authentication, parsing and state mutations.

The deadline covers receiving a body only. A valid gameplay replay/payment
handler retains its own operation budget. No incoming content is logged.
"""
import json
import math

from anyio import fail_after
from starlette.responses import JSONResponse

MAX_BODY = 65_536
MAX_JSON_DEPTH = 64
BODY_TIMEOUT_SECONDS = 15


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def _invalid_constant(_):
    raise ValueError('nonfinite_json_number')


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('nonfinite_json_number')
    return number


def _validate_json(body):
    # Decode explicitly: json.loads(bytes) also accepts UTF-16/32, unlike the
    # game's strict UTF-8 transport and the interchange format used here.
    text = body.decode('utf-8', errors='strict')
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError('json_too_deep')
        elif char in ']}':
            depth -= 1
    value = json.loads(text, object_pairs_hook=_unique_object,
                       parse_constant=_invalid_constant, parse_float=_finite_float)
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            item.encode('utf-8', errors='strict')
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


class BoundedBody:
    def __init__(self, app, body_timeout_seconds=BODY_TIMEOUT_SECONDS):
        if (type(body_timeout_seconds) not in (int, float)
                or not math.isfinite(body_timeout_seconds) or not 0.01 <= body_timeout_seconds <= 60):
            raise ValueError('invalid_body_timeout')
        self.app, self.body_timeout_seconds = app, body_timeout_seconds

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        body, oversized = bytearray(), False
        try:
            with fail_after(self.body_timeout_seconds):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    chunk = message.get('body', b'')
                    # Reject before allocating/copying a too-large chunk.
                    if len(chunk) > MAX_BODY - len(body):
                        oversized = True
                        break
                    body.extend(chunk)
                    if not message.get('more_body'):
                        break
        except TimeoutError:
            return await JSONResponse({'error': 'request_body_timeout'}, status_code=408)(scope, receive, send)
        if oversized:
            # Sending an error may encounter backpressure too. The receive-only
            # deadline must never turn that into a second/different response.
            return await JSONResponse({'error': 'body_too_large'}, status_code=413)(scope, receive, send)

        content_types = [v.decode('latin-1').split(';')[0].strip().lower()
                         for k, v in scope.get('headers', []) if k.lower() == b'content-type']
        json_body = not content_types or any(v == 'application/json' or
                        v.startswith('application/') and v.endswith('+json') for v in content_types)
        if body and json_body:
            try:
                _validate_json(body)
            except (ValueError, UnicodeError, RecursionError, OverflowError):
                return await JSONResponse({'error': 'invalid_request'}, status_code=422)(scope, receive, send)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)

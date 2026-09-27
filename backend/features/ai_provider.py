"""Explicit connection testing for OpenAI-compatible AI providers."""

import json
from typing import Any, Dict
from urllib.parse import urlsplit

from requests import RequestException, Session

from backend.base.custom_exceptions import InvalidKeyValue
from backend.base.definitions import Constants


def validate_setting(key: str, value: Any) -> Any:
    """Validate provider settings without echoing credentials in errors."""
    if key == 'ai_timeout':
        if type(value) is not int or not 5 <= value <= 120:
            raise InvalidKeyValue(key, 'Use a timeout between 5 and 120 seconds')
        return value
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise InvalidKeyValue(key, 'Use a single-line value of at most 2048 characters')
    value = value.strip()
    if key == 'ai_base_url' and value:
        try:
            parsed = urlsplit(value)
            valid = (parsed.scheme in ('http', 'https') and parsed.hostname
                     and not parsed.username and not parsed.password
                     and not parsed.query and not parsed.fragment)
            parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise InvalidKeyValue(key, 'Use an HTTP(S) API base URL without credentials, query or fragment')
        value = value.rstrip('/')
    return value


def test_connection(data: object) -> Dict[str, Any]:
    """Request a small model reply; never save settings or expose provider errors."""
    from backend.internals.settings import Settings

    if not isinstance(data, dict):
        raise InvalidKeyValue('body', 'Expected provider settings')
    saved = Settings().sv
    url = validate_setting('ai_base_url', data.get('ai_base_url', saved.ai_base_url))
    model = validate_setting('ai_model', data.get('ai_model', saved.ai_model))
    timeout = validate_setting('ai_timeout', data.get('ai_timeout', saved.ai_timeout))
    key = validate_setting('ai_api_key', data.get('ai_api_key', Constants.CREDENTIAL_REPLACEMENT))
    if not url or not model:
        raise InvalidKeyValue('ai_base_url', 'Enter an API base URL and model')
    if key == Constants.CREDENTIAL_REPLACEMENT:
        if url != saved.ai_base_url:
            raise InvalidKeyValue('ai_api_key', 'Enter the key again when testing a different endpoint')
        key = saved.ai_api_key
    headers = {'Accept': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    try:
        with Session() as session:
            session.trust_env = False
            with session.post(
                url + '/chat/completions', headers=headers,
                json={'model': model, 'messages': [{'role': 'user', 'content': 'Reply with OK.'}],
                      'max_tokens': 32, 'stream': False},
                timeout=(5, timeout), allow_redirects=False, stream=True
            ) as response:
                if response.status_code != 200:
                    messages = {401: 'Authentication failed. Check the API key.',
                                403: 'Provider denied access. Check key permissions.',
                                404: 'Endpoint or model not found. Check the base URL and model.',
                                429: 'Provider rate limit or quota reached.'}
                    return {'success': False, 'message': messages.get(
                        response.status_code, 'Provider returned HTTP ' + str(response.status_code))}
                body = bytearray()
                for chunk in response.iter_content(4096):
                    body.extend(chunk)
                    if len(body) > 65536:
                        return {'success': False, 'message': 'Provider response exceeded the test size limit.'}
                result = json.loads(body)
                content = result['choices'][0]['message']['content']
                if not isinstance(content, str) or not content.strip():
                    raise ValueError('Missing reply')
    except RequestException:
        return {'success': False, 'message': 'Connection failed or timed out. Check the endpoint, TLS and network access from Kapowarr.'}
    except (ValueError, KeyError, IndexError, TypeError):
        return {'success': False, 'message': 'Provider did not return a valid chat completion.'}
    return {'success': True, 'message': 'Connection successful; the model returned a reply.'}

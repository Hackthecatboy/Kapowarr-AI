"""AI provider settings and bounded connection tests without network access."""
import json
import sqlite3
import socket
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
from requests import Timeout
from requests.exceptions import ConnectTimeout, ReadTimeout, SSLError, ConnectionError
from urllib3.exceptions import ReadTimeoutError

from backend.base.custom_exceptions import InvalidKeyValue
from backend.base.definitions import Constants
from backend.features.ai_provider import test_connection, validate_setting, connection_error
from backend.internals.settings import Settings, SettingsValues
from frontend.api import api


class AIProvider(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(sv=SettingsValues(
            ai_base_url='http://model:11434/v1', ai_api_key='secret', ai_model='fixture'))
        p = patch('backend.internals.settings.Settings', return_value=self.settings)
        p.start(); self.addCleanup(p.stop)
        p = patch('backend.features.ai_provider.Session')
        self.factory = p.start(); self.addCleanup(p.stop)
        self.session = self.factory.return_value.__enter__.return_value
        self.response = self.session.post.return_value.__enter__.return_value
        self.response.status_code = 200
        self.response.iter_content.return_value = [json.dumps({'choices': [{'message': {'content': 'OK'}}]}).encode()]

    def test_saved_key_and_real_completion_request(self):
        self.assertTrue(test_connection({})['success'])
        args, kwargs = self.session.post.call_args
        self.assertEqual(args[0], 'http://model:11434/v1/chat/completions')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer secret')
        self.assertFalse(kwargs['allow_redirects'])
        self.assertFalse(self.session.trust_env)
        self.assertEqual(kwargs['json']['model'], 'fixture')

    def test_keyless_and_changed_endpoint(self):
        with self.assertRaises(InvalidKeyValue):
            test_connection({'ai_base_url': 'http://other/v1'})
        self.session.post.assert_not_called()
        self.assertTrue(test_connection({'ai_base_url': 'http://other/v1', 'ai_api_key': ''})['success'])
        self.assertNotIn('Authorization', self.session.post.call_args.kwargs['headers'])

    def test_errors_are_generic_and_do_not_echo_provider_body(self):
        for status in (301, 401, 403, 404, 429, 500):
            self.response.status_code = status
            result = test_connection({})
            self.assertFalse(result['success'])
            self.assertNotIn('secret', result['message'])
        self.session.post.side_effect = Timeout('secret provider URL')
        result = test_connection({})
        self.assertFalse(result['success'])
        self.assertNotIn('secret', result['message'])

    def test_transport_diagnostics_do_not_echo_sensitive_exception_text(self):
        for error, expected in (
            (SSLError('secret'), 'TLS'),
            (ConnectTimeout('secret'), 'before reaching'),
            (ReadTimeout('secret'), '30 seconds'),
            (ConnectionError(ReadTimeoutError(None, 'secret', 'secret')), '30 seconds'),
            (ConnectionError(socket.gaierror('secret')), 'DNS'),
            (ConnectionError(ConnectionRefusedError('secret')), 'refused'),
            (ConnectionError('secret'), 'interrupted'),
        ):
            message = connection_error(error, 30)
            self.assertIn(expected, message)
            self.assertNotIn('secret', message)

    def test_invalid_and_oversized_completion(self):
        for body in (b'{}', b'[]', b'not json', b'x' * 65537,
                     b'{"choices":[{"message":{"content":""}}]}'):
            self.response.iter_content.return_value = [body]
            self.assertFalse(test_connection({})['success'])

    def test_validation_and_authentication(self):
        for url in ('file:///tmp/model', 'http://user:secret@host/v1', 'https://host/v1?key=secret', 'http://host:bad'):
            with self.assertRaises(InvalidKeyValue):
                validate_setting('ai_base_url', url)
        for timeout in (True, 0, 121, '30'):
            with self.assertRaises(InvalidKeyValue):
                validate_setting('ai_timeout', timeout)
        self.assertEqual(validate_setting('ai_base_url', 'http://172.28.1.2:8000/v1/'), 'http://172.28.1.2:8000/v1')
        app = Flask(__name__)
        app.register_blueprint(api, url_prefix='/api')
        self.assertEqual(app.test_client().post('/api/ai/test', json={}).status_code, 401)


class AISettings(unittest.TestCase):
    def test_saved_key_is_masked_preserved_cleared_and_not_logged(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE config(key PRIMARY KEY, value)')
        db.executemany('INSERT INTO config VALUES(?,?)', [('ai_api_key', ''), ('ai_base_url', ''), ('ai_model', ''), ('ai_timeout', 30)])
        settings = object.__new__(Settings)
        settings.clear_cache(); self.addCleanup(settings.clear_cache)
        with patch('backend.internals.settings.get_db', return_value=db.cursor()), patch('backend.internals.settings.LOGGER') as logger:
            settings.update({'ai_api_key': 'test-secret'}, from_public=True)
            self.assertEqual(settings.get_public_settings().todict()['ai_api_key'], Constants.CREDENTIAL_REPLACEMENT)
            self.assertNotIn('test-secret', str(logger.info.call_args_list))
            settings.update({'ai_api_key': Constants.CREDENTIAL_REPLACEMENT}, from_public=True)
            self.assertEqual(settings.sv.ai_api_key, 'test-secret')
            settings.update({'ai_api_key': ''}, from_public=True)
            self.assertEqual(settings.sv.ai_api_key, '')
